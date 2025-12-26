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
    from ..utils.logging_config import get_logger
    logger = get_logger("security")

    status = "EXECUTED" if executed else "BLOCKED"
    logger.warning(f"[{status}] Dangerous command detected: {reason}")
    logger.warning(f"Command: {command[:200]}...")  # Truncate for safety


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
    Check if a command is potentially dangerous.

    Args:
        command: Command to check

    Returns:
        Tuple of (is_dangerous, reason)
    """
    dangerous_patterns = [
        # Destructive file operations
        ('rm -rf /', "Recursive delete of root filesystem"),
        ('rm -rf ~', "Recursive delete of home directory"),
        ('rm -rf /*', "Recursive delete of all root contents"),
        ('del /f /s /q', "Force delete all files (Windows)"),
        ('rd /s /q', "Remove directory tree (Windows)"),

        # Disk operations
        ('format', "Format disk"),
        ('fdisk', "Partition disk"),
        ('dd if=', "Direct disk write"),
        ('mkfs', "Create filesystem"),
        ('wipefs', "Wipe filesystem signatures"),
        ('shred', "Secure delete/overwrite"),

        # System control
        ('shutdown', "System shutdown"),
        ('reboot', "System reboot"),
        ('halt', "System halt"),
        ('poweroff', "System power off"),
        ('init 0', "System halt via init"),
        ('init 6', "System reboot via init"),

        # Permission changes
        ('chown -R', "Recursive ownership change"),
        ('chmod -R 777', "Recursive world-writable permissions"),
        ('chmod -R 000', "Recursive remove all permissions"),

        # Privilege escalation
        ('sudo su', "Switch to root user"),
        ('su root', "Switch to root user"),
        ('sudo -i', "Interactive root shell"),

        # Remote code execution
        ('curl | bash', "Pipe remote script to shell"),
        ('curl | sh', "Pipe remote script to shell"),
        ('wget | bash', "Pipe remote script to shell"),
        ('wget | sh', "Pipe remote script to shell"),
        ('$(curl', "Command substitution with curl"),
        ('$(wget', "Command substitution with wget"),
        ('`curl', "Backtick substitution with curl"),
        ('`wget', "Backtick substitution with wget"),

        # Code execution
        ('eval $', "Eval with variable expansion"),
        ('eval "', "Eval with string"),
        ("eval '", "Eval with string"),
        ('exec(', "Python exec"),
        ('python -c', "Python command execution"),
        ('perl -e', "Perl command execution"),
        ('ruby -e', "Ruby command execution"),

        # Network attacks
        (':(){ :|:& };:', "Fork bomb"),
        ('> /dev/sda', "Write to disk device"),
        ('> /dev/null', "Redirect to null (data loss risk)"),
        ('mkfifo', "Create named pipe (can be used for attacks)"),

        # Credential access
        ('cat /etc/shadow', "Read password hashes"),
        ('cat /etc/passwd', "Read user database"),
        ('cat ~/.ssh', "Read SSH keys"),
        ('cat ~/.aws', "Read AWS credentials"),

        # Git destructive
        ('git push --force', "Force push (can lose commits)"),
        ('git push -f', "Force push (can lose commits)"),
        ('git reset --hard', "Hard reset (loses uncommitted changes)"),
        ('git clean -fd', "Remove untracked files"),
    ]

    command_lower = command.lower()

    for pattern, reason in dangerous_patterns:
        if pattern in command_lower:
            return True, reason

    # Check for obfuscation
    if command_lower.count('|') > 3:
        return True, "Excessive pipe chaining (potential obfuscation)"

    if command_lower.count(';') > 5:
        return True, "Excessive command chaining (potential obfuscation)"

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