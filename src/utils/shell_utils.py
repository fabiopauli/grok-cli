#!/usr/bin/env python3

"""
Shell utilities for Grok Assistant

Handles shell command execution with security controls.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Union, Tuple

from ..core.config import Config
from ..utils.logging_config import get_logger


def detect_available_shells(config: Config) -> None:
    """
    Detect which shells are available on the system.
    
    Args:
        config: Configuration object to update
    """
    shells = ['bash', 'zsh', 'powershell', 'cmd']
    
    for shell in shells:
        if shell == 'cmd' and config.os_info['is_windows']:
            # cmd is always available on Windows
            config.os_info['shell_available'][shell] = True
        elif shell == 'powershell':
            # Check for both Windows PowerShell and PowerShell Core
            config.os_info['shell_available'][shell] = (
                shutil.which('powershell') is not None or 
                shutil.which('pwsh') is not None
            )
        else:
            config.os_info['shell_available'][shell] = shutil.which(shell) is not None


def log_dangerous_command(command: str, reason: str, executed: bool = False) -> None:
    """
    Log a dangerous command for audit purposes.

    Args:
        command: The command that was detected
        reason: Why it was flagged as dangerous
        executed: Whether it was actually executed
    """
    logger = get_logger("security")

    status = "EXECUTED" if executed else "BLOCKED"
    # Truncate command for safety (max 200 chars)
    truncated_command = command[:200] + "..." if len(command) > 200 else command
    logger.warning(f"[{status}] Dangerous command detected: {reason}\nCommand: {truncated_command}")


def run_bash_command(command: str, config: Config,
                    cwd: Optional[Union[str, Path]] = None) -> str:
    """
    Execute a bash command with security confirmation.

    Args:
        command: Command to execute
        config: Configuration object
        cwd: Working directory

    Returns:
        Command output
    """
    # Import here to avoid circular imports
    from ..ui.console import display_security_confirmation, get_console

    # Check for dangerous commands
    is_dangerous, reason = is_dangerous_command(command)

    if is_dangerous:
        log_dangerous_command(command, reason, executed=False)

        if not config.agent_mode:
            # Always require confirmation for dangerous commands
            console = get_console()
            console.print(f"[bold red]⚠️  DANGEROUS COMMAND DETECTED[/bold red]")
            console.print(f"[yellow]Reason: {reason}[/yellow]")

            if not display_security_confirmation(command, "bash"):
                return f"Command blocked: {reason}"
        else:
            # In agent mode, log but allow (with warning)
            log_dangerous_command(command, reason, executed=True)

    # Security confirmation (skip if agent mode is enabled)
    if config.require_bash_confirmation and not config.agent_mode and not is_dangerous:
        if not display_security_confirmation(command, "bash"):
            return "Command execution cancelled by user."
    
    # Set working directory
    if cwd is None:
        cwd = config.base_dir
    
    try:
        # Use bash explicitly to ensure consistent behavior
        result = subprocess.run(
            ['bash', '-c', command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        # Format output with truncation
        output_parts = []

        if result.stdout:
            truncated_stdout = truncate_shell_output(
                result.stdout,
                config.shell_output_max_lines,
                config.shell_output_max_chars
            )
            output_parts.append(f"stdout:\n{truncated_stdout}")

        if result.stderr:
            truncated_stderr = truncate_shell_output(
                result.stderr,
                config.shell_output_max_lines // 2,  # Less space for stderr
                config.shell_output_max_chars // 2
            )
            output_parts.append(f"stderr:\n{truncated_stderr}")

        if result.returncode != 0:
            output_parts.append(f"Exit code: {result.returncode}")

        return "\n".join(output_parts) if output_parts else "Command completed with no output."
        
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 30 seconds: {command}"
    except FileNotFoundError:
        return "Error: bash not found. Please ensure bash is installed and in your PATH."
    except Exception as e:
        return f"Error executing bash command: {str(e)}"


def truncate_shell_output(output: str, max_lines: int, max_chars: int) -> str:
    """
    Truncate shell output preserving head and tail for context.

    Args:
        output: Shell output to truncate
        max_lines: Maximum number of lines to keep
        max_chars: Maximum number of characters to keep

    Returns:
        Truncated output string
    """
    # Char limit check first
    if len(output) > max_chars:
        output = output[:max_chars] + f"\n... (truncated {len(output) - max_chars} chars)"

    lines = output.splitlines()
    if len(lines) <= max_lines:
        return output

    # Keep first 30% (context) and last 70% (recent output)
    head_lines = int(max_lines * 0.3)
    tail_lines = max_lines - head_lines

    truncated = (
        lines[:head_lines] +
        [f"... ({len(lines) - max_lines} lines truncated) ..."] +
        lines[-tail_lines:]
    )
    return "\n".join(truncated)


def run_powershell_command(command: str, config: Config, 
                          cwd: Optional[Union[str, Path]] = None) -> str:
    """
    Execute a PowerShell command with security confirmation.
    
    Args:
        command: Command to execute
        config: Configuration object
        cwd: Working directory
        
    Returns:
        Command output
    """
    # Import here to avoid circular imports
    from ..ui.console import display_security_confirmation

    # Security confirmation (skip if agent mode is enabled)
    if config.require_powershell_confirmation and not config.agent_mode:
        if not display_security_confirmation(command, "powershell"):
            return "Command execution cancelled by user."
    
    # Set working directory
    if cwd is None:
        cwd = config.base_dir
    
    try:
        # Try PowerShell Core first (pwsh), then Windows PowerShell
        powershell_exe = 'pwsh' if shutil.which('pwsh') else 'powershell'
        
        # Use -Command parameter for better compatibility
        result = subprocess.run(
            [powershell_exe, '-Command', command],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        # Format output with truncation
        output_parts = []

        if result.stdout:
            truncated_stdout = truncate_shell_output(
                result.stdout,
                config.shell_output_max_lines,
                config.shell_output_max_chars
            )
            output_parts.append(f"stdout:\n{truncated_stdout}")

        if result.stderr:
            truncated_stderr = truncate_shell_output(
                result.stderr,
                config.shell_output_max_lines // 2,  # Less space for stderr
                config.shell_output_max_chars // 2
            )
            output_parts.append(f"stderr:\n{truncated_stderr}")

        if result.returncode != 0:
            output_parts.append(f"Exit code: {result.returncode}")

        return "\n".join(output_parts) if output_parts else "Command completed with no output."
        
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after 30 seconds: {command}"
    except FileNotFoundError:
        return f"Error: {powershell_exe} not found. Please ensure PowerShell is installed and in your PATH."
    except Exception as e:
        return f"Error executing PowerShell command: {str(e)}"


def get_shell_for_os(config: Config) -> str:
    """
    Get the appropriate shell for the current OS.
    
    Args:
        config: Configuration object
        
    Returns:
        Shell name
    """
    if config.os_info['is_windows']:
        if config.os_info['shell_available']['powershell']:
            return 'powershell'
        elif config.os_info['shell_available']['cmd']:
            return 'cmd'
    else:
        if config.os_info['shell_available']['bash']:
            return 'bash'
        elif config.os_info['shell_available']['zsh']:
            return 'zsh'
    
    return 'unknown'


def is_dangerous_command(command: str) -> tuple[bool, str]:
    """
    Check if a command is potentially dangerous (truly destructive operations only).

    Args:
        command: Command to check

    Returns:
        Tuple of (is_dangerous, reason)
    """
    import re

    command_lower = command.lower()

    # Destructive file operations
    if re.search(r'\brm\b.*-rf\b', command_lower):
        return True, "Recursive delete (rm -rf)"

    if 'del /f /s /q' in command_lower or 'rd /s /q' in command_lower:
        return True, "Force delete all files (Windows)"

    # Disk operations
    for pattern in ['format', 'fdisk', 'dd if=', 'mkfs', 'wipefs', 'shred']:
        if pattern in command_lower:
            return True, f"Dangerous disk operation: {pattern}"

    # System control
    for pattern in ['shutdown', 'reboot', 'halt', 'poweroff', 'init 0', 'init 6']:
        if pattern in command_lower:
            return True, f"System control: {pattern}"

    # Fork bomb
    if ':(){ :|:& };:' in command_lower:
        return True, "Fork bomb"

    # Write to disk device
    if '> /dev/sda' in command_lower or '> /dev/sd' in command_lower:
        return True, "Write to disk device"

    return False, ""


def sanitize_command(command: str) -> str:
    """
    Sanitize a command by removing dangerous elements.
    
    Args:
        command: Command to sanitize
        
    Returns:
        Sanitized command
    """
    # Remove null bytes
    command = command.replace('\x00', '')
    
    # Remove control characters
    command = ''.join(char for char in command if ord(char) >= 32 or char in '\t\n\r')
    
    # Limit length
    if len(command) > 1000:
        command = command[:1000]
    
    return command.strip()


def validate_working_directory(cwd: Union[str, Path], config: Config) -> bool:
    """
    Validate that a working directory is safe to use.
    
    Args:
        cwd: Working directory path
        config: Configuration object
        
    Returns:
        True if directory is safe, False otherwise
    """
    try:
        cwd_path = Path(cwd).resolve()
        
        # Check if directory exists
        if not cwd_path.exists() or not cwd_path.is_dir():
            return False
        
        # Check if directory is within base directory
        try:
            cwd_path.relative_to(config.base_dir)
            return True
        except ValueError:
            # Directory is outside base directory
            return False
    
    except (OSError, ValueError):
        return False