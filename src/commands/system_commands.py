#!/usr/bin/env python3

"""
System commands for Grok Assistant

Commands that handle system-level operations like exit, clear, help, etc.
"""

import sys
from typing import Dict, Any

from .base import BaseCommand, CommandResult
from ..core.session import GrokSession


class ExitCommand(BaseCommand):
    """Handle /exit and /quit commands."""
    
    def get_pattern(self) -> str:
        return "/exit"
    
    def get_description(self) -> str:
        return "Exit the application (/exit or /quit)"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() in ("/exit", "/quit")
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        console = get_console()
        console.print("[bold blue]👋 Goodbye![/bold blue]")
        sys.exit(0)


class ClearCommand(BaseCommand):
    """Handle /clear command to clear screen."""
    
    def get_pattern(self) -> str:
        return "/clear"
    
    def get_description(self) -> str:
        return "Clear the screen"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/clear"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        console = get_console()
        console.clear()
        return CommandResult.success()


class HelpCommand(BaseCommand):
    """Handle /help command to show available commands."""
    
    def get_pattern(self) -> str:
        return "/help"
    
    def get_description(self) -> str:
        return "Show available commands and usage information"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/help"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from rich.panel import Panel
        
        console = get_console()
        
        help_text = f"""
**Grok Assistant** - Your AI-powered development companion

**Available Commands:**
• `/add <path>` - Add file/directory to context with fuzzy matching
• `/remove <path>` - Remove file from context
• `/fuzzy` - Toggle fuzzy matching mode (currently: {'enabled' if self.config.fuzzy_enabled_by_default else 'disabled'})
• `/folder <path>` - Change working directory
• `/clear` - Clear screen
• `/clear context` - Clear conversation history
• `/context` - Show context usage statistics
• `/log` - Show recent conversation history
• `/r1` - Get one response from Grok-4 reasoning model without switching
• `/reasoner` - Toggle between Grok-3 and Grok-4 reasoning model
• `/os` - Show OS and environment information
• `/help` - Show this help message
• `/exit` or `/quit` - Exit the application

**File Operations:**
Grok can read, create, and edit files through natural conversation. Just describe what you want to do!

**System Commands:**
Use run_bash (Linux/macOS) or run_powershell (Windows) for system operations.

**Security Features:**
• Fuzzy matching is opt-in for security
• Shell commands require confirmation
• Path validation prevents directory traversal

**Tips:**
• Use `/add` to include files in your conversation context
• Try `/fuzzy` to enable more flexible file matching
• Use `/context` to monitor token usage
• Natural language works best - just describe what you need!
"""
        
        console.print(Panel(help_text, title="🚀 Grok Assistant Help", border_style="bright_blue"))
        return CommandResult.success()


class OsCommand(BaseCommand):
    """Handle /os command to show OS information."""
    
    def get_pattern(self) -> str:
        return "/os"
    
    def get_description(self) -> str:
        return "Show OS and environment information"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/os"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from rich.table import Table
        
        console = get_console()
        os_info = self.config.os_info
        
        # Create OS information table
        os_table = Table(title="🖥️ Operating System Information", show_header=True, header_style="bold bright_blue")
        os_table.add_column("Property", style="bright_cyan")
        os_table.add_column("Value", style="white")
        
        os_table.add_row("System", os_info['system'])
        os_table.add_row("Release", os_info['release'])
        os_table.add_row("Version", os_info['version'])
        os_table.add_row("Machine", os_info['machine'])
        os_table.add_row("Processor", os_info['processor'])
        os_table.add_row("Python Version", os_info['python_version'])
        
        console.print(os_table)
        
        # Create shell availability table
        shell_table = Table(title="🐚 Shell Availability", show_header=True, header_style="bold bright_green")
        shell_table.add_column("Shell", style="bright_cyan")
        shell_table.add_column("Available", style="white")
        
        for shell, available in os_info['shell_available'].items():
            status = "✅ Available" if available else "❌ Not Available"
            shell_table.add_row(shell, status)
        
        console.print(shell_table)
        
        # Show current working directory
        console.print(f"\n📁 Current Working Directory: [bright_cyan]{self.config.base_dir}[/bright_cyan]")
        
        return CommandResult.success()


class FuzzyCommand(BaseCommand):
    """Handle /fuzzy command to toggle fuzzy matching."""
    
    def get_pattern(self) -> str:
        return "/fuzzy"
    
    def get_description(self) -> str:
        return "Toggle fuzzy matching mode for file operations"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/fuzzy"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        
        if not self.config.fuzzy_available:
            console.print("[bold red]✗[/bold red] Fuzzy matching is not available. Install 'thefuzz' package.")
            return CommandResult.failure("Fuzzy matching not available")
        
        # Toggle fuzzy mode
        if self.config.fuzzy_enabled_by_default:
            session.disable_fuzzy_mode()
            console.print("[bold green]✓[/bold green] Fuzzy matching disabled for this session.")
        else:
            session.enable_fuzzy_mode()
            console.print("[bold green]✓[/bold green] Fuzzy matching enabled for this session.")
        
        return CommandResult.success()