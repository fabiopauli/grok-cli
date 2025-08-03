#!/usr/bin/env python3

"""
Context management commands for Grok Assistant

Commands that handle conversation context, model switching, etc.
"""

from .base import BaseCommand, CommandResult
from ..core.session import GrokSession



class ContextCommand(BaseCommand):
    """Handle /context command to show context usage statistics."""
    
    def get_pattern(self) -> str:
        return "/context"
    
    def get_description(self) -> str:
        return "Show context usage statistics"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/context"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from rich.table import Table
        
        console = get_console()
        context_info = session.get_context_info()
        
        context_table = Table(title="📊 Context Usage Statistics", show_header=True, header_style="bold bright_blue")
        context_table.add_column("Metric", style="bright_cyan")
        context_table.add_column("Value", style="white")
        
        context_table.add_row("Model", context_info['model'])
        context_table.add_row("Messages", str(context_info['messages']))
        context_table.add_row("Estimated Tokens", f"{context_info['estimated_tokens']:,}")
        context_table.add_row("Max Tokens", f"{context_info['max_tokens']:,}")
        context_table.add_row("Usage %", f"{context_info['token_usage_percent']:.1f}%")
        
        # Color-code status
        if context_info['critical_limit']:
            status = "[bold red]🔴 Critical[/bold red]"
        elif context_info['approaching_limit']:
            status = "[bold yellow]🟡 High[/bold yellow]"
        else:
            status = "[bold green]🟢 Normal[/bold green]"
        
        context_table.add_row("Status", status)
        
        console.print(context_table)
        
        # Show recommendations
        if context_info['critical_limit']:
            console.print("\n[bold red]⚠ Context is critical![/bold red]")
            console.print("[dim]Consider using /clear context to reduce token usage.[/dim]")
        elif context_info['approaching_limit']:
            console.print("\n[bold yellow]⚠ Context is getting high.[/bold yellow]")
            console.print("[dim]Monitor usage to avoid context limits.[/dim]")
        
        return CommandResult.success()


class LogCommand(BaseCommand):
    """Handle /log command to show recent conversation history."""
    
    def get_pattern(self) -> str:
        return "/log"
    
    def get_description(self) -> str:
        return "Show recent conversation history"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/log"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from ..ui.formatters import format_conversation_log
        
        console = get_console()
        conversation_history = session.get_conversation_history()
        
        if len(conversation_history) <= 1:
            console.print("[yellow]No conversation history available.[/yellow]")
            return CommandResult.success()
        
        # Show recent history (last 10 messages, excluding system messages)
        recent_messages = [msg for msg in conversation_history[-10:] if msg["role"] != "system"]
        
        if not recent_messages:
            console.print("[yellow]No user/assistant messages in recent history.[/yellow]")
            return CommandResult.success()
        
        format_conversation_log(recent_messages, console)
        return CommandResult.success()


class ReasonerCommand(BaseCommand):
    """Handle /reasoner command to toggle between models."""
    
    def get_pattern(self) -> str:
        return "/reasoner"
    
    def get_description(self) -> str:
        return "Toggle between Grok-3 and Grok-4 reasoning model"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/reasoner"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        
        if session.model == self.config.reasoner_model:
            # Switch back to default model
            session.switch_model(self.config.default_model)
            console.print(f"[bold green]✓[/bold green] Switched to {self.config.default_model} model")
        else:
            # Switch to reasoner model
            session.switch_model(self.config.reasoner_model)
            console.print(f"[bold green]✓[/bold green] Switched to {self.config.reasoner_model} reasoning model")
            console.print("[dim]This model provides enhanced reasoning capabilities.[/dim]")
        
        return CommandResult.success()


class OneTimeReasonerCommand(BaseCommand):
    """Handle /r1 command for one-off reasoner response."""
    
    def get_pattern(self) -> str:
        return "/r1"
    
    def get_description(self) -> str:
        return "Get one response from Grok-4 reasoning model without switching"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/r1"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        
        if session.model == self.config.reasoner_model:
            console.print(f"[yellow]Already using {self.config.reasoner_model} model.[/yellow]")
            return CommandResult.success()
        
        # Set flag for one-time reasoner use
        session._use_reasoner_next = True
        console.print(f"[bold green]✓[/bold green] Next response will use {self.config.reasoner_model} reasoning model")
        console.print("[dim]This model provides enhanced reasoning capabilities.[/dim]")
        
        return CommandResult.success()


class DefaultModelCommand(BaseCommand):
    """Handle switching back to default model."""
    
    def get_pattern(self) -> str:
        return "/default"
    
    def get_description(self) -> str:
        return "Switch back to default model"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/default"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        
        if session.model == self.config.default_model:
            console.print(f"[yellow]Already using {self.config.default_model} model.[/yellow]")
            return CommandResult.success()
        
        # Switch to default model
        session.switch_model(self.config.default_model)
        console.print(f"[bold green]✓[/bold green] Switched to {self.config.default_model} model")
        
        return CommandResult.success()


class ContextModeCommand(BaseCommand):
    """Handle /context-mode command to show current context mode and options."""
    
    def get_pattern(self) -> str:
        return "/context-mode"
    
    def get_description(self) -> str:
        return "Show current context management mode and toggle options"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/context-mode"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        from rich.table import Table
        
        console = get_console()
        current_mode = session.get_context_mode()
        
        # Display current mode
        console.print(f"\n[bold cyan]Current Context Mode:[/bold cyan] {current_mode}")
        
        # Create mode comparison table
        mode_table = Table(title="Context Management Modes", show_header=True, header_style="bold bright_blue")
        mode_table.add_column("Mode", style="bright_cyan")
        mode_table.add_column("Description", style="white")
        mode_table.add_column("Best For", style="green")
        mode_table.add_column("Active", style="yellow")
        
        cache_active = "✓" if current_mode == "cache_optimized" else ""
        smart_active = "✓" if current_mode == "smart_truncation" else ""
        
        mode_table.add_row(
            "cache_optimized",
            "Sequential context with periodic truncation",
            "Long conversations, preserving history",
            cache_active
        )
        mode_table.add_row(
            "smart_truncation", 
            "Immediate turn summarization at 70% limit",
            "Memory-efficient, frequent API calls",
            smart_active
        )
        
        console.print(mode_table)
        
        # Show commands to switch modes
        console.print("\n[bold]Commands:[/bold]")
        console.print("  [cyan]/sequential[/cyan] - Switch to cache_optimized mode")
        console.print("  [cyan]/smart[/cyan] - Switch to smart_truncation mode")
        
        return CommandResult.success()


class SequentialContextCommand(BaseCommand):
    """Handle /sequential command to switch to cache-optimized context mode."""
    
    def get_pattern(self) -> str:
        return "/sequential"
    
    def get_description(self) -> str:
        return "Switch to cache-optimized (sequential) context mode"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/sequential"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        current_mode = session.get_context_mode()
        
        if current_mode == "cache_optimized":
            console.print("[yellow]Already using cache-optimized (sequential) context mode.[/yellow]")
            return CommandResult.success()
        
        # Switch to cache-optimized mode
        session.set_context_mode("cache_optimized")
        console.print("[bold green]✓[/bold green] Switched to cache-optimized (sequential) context mode")
        console.print("[dim]Context will be preserved sequentially with periodic truncation when limits are reached.[/dim]")
        
        return CommandResult.success()


class SmartTruncationCommand(BaseCommand):
    """Handle /smart command to switch to smart truncation context mode."""
    
    def get_pattern(self) -> str:
        return "/smart"
    
    def get_description(self) -> str:
        return "Switch to smart truncation context mode"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/smart"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console
        
        console = get_console()
        current_mode = session.get_context_mode()
        
        if current_mode == "smart_truncation":
            console.print("[yellow]Already using smart truncation context mode.[/yellow]")
            return CommandResult.success()
        
        # Switch to smart truncation mode
        session.set_context_mode("smart_truncation")
        console.print("[bold green]✓[/bold green] Switched to smart truncation context mode")
        console.print("[dim]Context will be automatically summarized when reaching 70% token limit.[/dim]")
        
        return CommandResult.success()