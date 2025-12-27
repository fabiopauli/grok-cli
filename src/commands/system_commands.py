#!/usr/bin/env python3

"""
System commands for Grok Assistant

Commands that handle system-level operations like exit, clear, help, etc.
"""

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
        return CommandResult.exit("User requested exit")


class ClearScreenCommand(BaseCommand):
    """Handle /cls command to clear screen."""
    
    def get_pattern(self) -> str:
        return "/cls"
    
    def get_description(self) -> str:
        return "Clear the screen"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/cls"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        console = get_console()
        console.clear()
        return CommandResult.ok()


class ClearContextCommand(BaseCommand):
    """Handle /clear command to clear conversation context."""
    
    def get_pattern(self) -> str:
        return "/clear"
    
    def get_description(self) -> str:
        return "Clear conversation history"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/clear"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console, get_prompt_session
        
        console = get_console()
        prompt_session = get_prompt_session()
        
        conversation_history = session.get_conversation_history()
        
        if len(conversation_history) <= 1:
            console.print("[yellow]Context already empty (only system prompt).[/yellow]")
            return CommandResult.ok()
            
        file_contexts = sum(1 for msg in conversation_history if msg["role"] == "system" and "User added file" in msg["content"])
        total_messages = len(conversation_history) - 1
        
        console.print(f"[yellow]Current context: {total_messages} messages, {file_contexts} file contexts[/yellow]")
        
        # Confirm with user
        confirm = prompt_session.prompt("🔵 Are you sure you want to clear the context? (y/N): ", default="n").strip().lower()
        
        if confirm in ["y", "yes"]:
            session.clear_context(keep_system_prompt=True)
            console.print("[bold green]✓[/bold green] Context cleared (system prompt retained)")
            return CommandResult.ok()
        else:
            console.print("[yellow]Context clear cancelled.[/yellow]")
            return CommandResult.ok()


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

**File & Context Commands:**
• `/add <path>` - Add file/directory to context with fuzzy matching
• `/remove <path>` - Remove file from context
• `/folder <path>` - Change working directory
• `/context` - Show context usage statistics
• `/context-mode` - Show current context management mode and options
• `/sequential` - Switch to cache-optimized context mode (preserves history longer)
• `/smart` - Switch to smart truncation mode (summarizes at 70% usage)
• `/clear` - Clear conversation history
• `/log` - Show recent conversation history

**Memory Management:**
• `/memory` - Interactive memory management (save/load project knowledge)

**Model & Reasoning:**
• `/reasoner` or `/r` - Toggle between default and reasoning model (grok-4-1 family)
• `/coder` - Switch to grok-code-fast-1 coding model
• `/default` - Switch back to default model (grok-4-1-fast-non-reasoning)
• `/grok-4` - Switch to legacy grok-4-fast-non-reasoning model
• `/4r` - Switch to legacy grok-4-fast-reasoning model
• `/max` - Toggle extended 2M context for grok-4-1 models (default: 128K)

**System Commands:**
• `/fuzzy` - Toggle fuzzy matching mode (currently: {'enabled' if self.config.fuzzy_enabled_by_default else 'disabled'})
• `/agent` - Toggle agentic mode (removes safety confirmations)
• `/self` - Toggle self-evolving mode (AI can create custom tools)
• `/reload-tools` - Reload custom tools from ~/.grok/custom_tools/
• `/max-steps [N]` - Set maximum reasoning steps (default: 100, use 0 for unlimited)
• `/jobs` - List all background jobs
• `/cls` - Clear screen
• `/os` - Show OS and environment information
• `/help` - Show this help message
• `/exit` or `/quit` - Exit the application

**File Operations:**
Grok can read, create, and edit files through natural conversation. Just describe what you want to do!

**Shell Commands:**
Use run_bash (Linux/macOS) or run_powershell (Windows) for system operations.
Use run_bash_background or run_powershell_background for long-running tasks in the background.

**Security Features:**
• Fuzzy matching is opt-in for security
• Shell commands require confirmation (unless `/agent` mode is enabled)
• Path validation prevents directory traversal
• Agent mode disabled by default for safety

**Tips:**
• Use `/add` to include files in your conversation context
• Try `/memory` to save important project knowledge and preferences
• Use `/fuzzy` to enable more flexible file matching
• Use `/agent` for autonomous operation (use with caution!)
• Use `/self` to enable AI to create custom tools (saved to ~/.grok/custom_tools/)
• Use `/context` to monitor token usage
• Natural language works best - just describe what you need!
"""

        console.print(Panel(help_text, title="🚀 Grok Assistant Help", border_style="bright_blue"))
        return CommandResult.ok()


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

        return CommandResult.ok()


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
            return CommandResult.fail("Fuzzy matching not available")

        # Toggle fuzzy mode
        if self.config.fuzzy_enabled_by_default:
            session.disable_fuzzy_mode()
            console.print("[bold green]✓[/bold green] Fuzzy matching disabled for this session.")
        else:
            session.enable_fuzzy_mode()
            console.print("[bold green]✓[/bold green] Fuzzy matching enabled for this session.")

        return CommandResult.ok()


class AgentCommand(BaseCommand):
    """Handle /agent command to toggle agentic mode."""

    def get_pattern(self) -> str:
        return "/agent"

    def get_description(self) -> str:
        return "Toggle agentic mode (removes safety confirmations)"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/agent"

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console

        console = get_console()

        # Toggle agent mode
        self.config.agent_mode = not self.config.agent_mode

        if self.config.agent_mode:
            console.print("[bold yellow]⚡ Agentic mode enabled[/bold yellow]")
            console.print("[dim]Shell commands will execute without confirmations.[/dim]")
            console.print("[yellow]⚠️  Warning: Use with caution - AI can now execute commands autonomously![/yellow]")
        else:
            console.print("[bold green]✓ Agentic mode disabled[/bold green]")
            console.print("[dim]Shell commands will require confirmation.[/dim]")

        return CommandResult.ok()


class MaxStepsCommand(BaseCommand):
    """Handle /max-steps command to set maximum reasoning steps."""

    def get_pattern(self) -> str:
        return "/max-steps"

    def get_description(self) -> str:
        return "Set maximum reasoning steps (tool call iterations)"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower().startswith("/max-steps")

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console

        console = get_console()

        args = self.extract_arguments(user_input).strip()

        # Show current setting if no argument
        if not args:
            current = self.config.max_reasoning_steps
            if current >= 999999:
                console.print(f"[cyan]Current maximum reasoning steps: Unlimited[/cyan]")
            else:
                console.print(f"[cyan]Current maximum reasoning steps: {current}[/cyan]")
            console.print("[dim]Usage: /max-steps <number> or /max-steps unlimited[/dim]")
            return CommandResult.ok()

        # Set unlimited
        if args.lower() in ["unlimited", "infinite", "0"]:
            self.config.max_reasoning_steps = 999999
            console.print("[bold green]✓ Maximum reasoning steps set to unlimited[/bold green]")
            console.print("[yellow]⚠️  Warning: AI can now execute unlimited tool calls![/yellow]")
            return CommandResult.ok()

        # Set specific number
        try:
            steps = int(args)
            if steps < 1:
                console.print("[bold red]✗[/bold red] Steps must be a positive number")
                return CommandResult.fail("Invalid step count")

            self.config.max_reasoning_steps = steps
            console.print(f"[bold green]✓ Maximum reasoning steps set to {steps}[/bold green]")
            return CommandResult.ok()

        except ValueError:
            console.print("[bold red]✗[/bold red] Invalid number. Usage: /max-steps <number> or /max-steps unlimited")
            return CommandResult.fail("Invalid argument")


class JobsCommand(BaseCommand):
    """Handle /jobs command to list background jobs."""

    def get_pattern(self) -> str:
        return "/jobs"

    def get_description(self) -> str:
        return "List all background jobs"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/jobs"

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from rich.table import Table

        console = get_console()

        # Check if background manager exists
        if not hasattr(self.config, '_background_manager'):
            console.print("[yellow]No background jobs running[/yellow]")
            return CommandResult.ok()

        manager = self.config._background_manager
        jobs = manager.list_jobs()

        if not jobs:
            console.print("[yellow]No background jobs[/yellow]")
            return CommandResult.ok()

        # Create table
        table = Table(title="🔧 Background Jobs", show_header=True, header_style="bold bright_blue")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Status", style="white", width=10)
        table.add_column("Shell", style="green", width=10)
        table.add_column("Runtime", style="yellow", width=10)
        table.add_column("Command", style="white")

        for job in jobs:
            is_running = job.is_running()
            status_str = f"{'🟢' if is_running else '🔴'} {job.status}"
            runtime_str = f"{job.get_runtime():.1f}s"
            command_str = job.command[:60] + "..." if len(job.command) > 60 else job.command

            table.add_row(
                str(job.job_id),
                status_str,
                job.shell_type,
                runtime_str,
                command_str
            )

        console.print(table)
        console.print(f"\n[dim]Total jobs: {len(jobs)}[/dim]")
        console.print("[dim]Use AI commands to check job output or kill jobs[/dim]")

        return CommandResult.ok()


class SelfModeCommand(BaseCommand):
    """Handle /self command to toggle self-evolving mode."""

    def get_pattern(self) -> str:
        return "/self"

    def get_description(self) -> str:
        return "Toggle self-evolving mode (AI can create new tools)"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/self"

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console

        console = get_console()

        # Toggle self-evolving mode
        self.config.self_mode = not getattr(self.config, 'self_mode', False)

        if self.config.self_mode:
            console.print("[bold yellow]🔧 Self-evolving mode enabled[/bold yellow]")
            console.print("[dim]AI can now create new tools. Tools are saved to ~/.grok/custom_tools/[/dim]")
            console.print("[yellow]⚠️  Tools cannot modify the system prompt.[/yellow]")

            # Add self-mode instructions to context
            session.add_message("system",
                "SELF-EVOLVING MODE ACTIVE: You can create new tools using create_tool(). "
                "Tools must inherit from BaseTool and have get_name() and execute() methods. "
                "Include a create_tool(config) factory function. "
                "Safety: No subprocess, eval, exec, or file system access outside allowed paths."
            )
        else:
            console.print("[bold green]✓ Self-evolving mode disabled[/bold green]")
            console.print("[dim]AI can no longer create new tools.[/dim]")

        return CommandResult.ok()


class ReloadToolsCommand(BaseCommand):
    """Handle /reload-tools command to reload custom tools."""

    def get_pattern(self) -> str:
        return "/reload-tools"

    def get_description(self) -> str:
        return "Reload custom tools from ~/.grok/custom_tools/"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/reload-tools"

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console

        console = get_console()

        # Access tool registry through session/config
        if not hasattr(self.config, '_tool_registry'):
            console.print("[yellow]No tool registry available[/yellow]")
            return CommandResult.fail("Tool registry not initialized")

        try:
            count = self.config._tool_registry.refresh_dynamic_tools(
                self.config._dynamic_loader
            )
            console.print(f"[bold green]✓ Reloaded {count} custom tool(s)[/bold green]")
            return CommandResult.ok()
        except Exception as e:
            console.print(f"[bold red]✗ Error reloading tools: {e}[/bold red]")
            return CommandResult.fail(str(e))