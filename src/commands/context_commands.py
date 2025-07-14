#!/usr/bin/env python3

"""
Context management commands for Grok Assistant

Commands that handle conversation context, model switching, etc.
"""

from .base import BaseCommand, CommandResult
from ..core.session import GrokSession


class ClearContextCommand(BaseCommand):
    """Handle /clear context command to clear conversation history."""
    
    def get_pattern(self) -> str:
        return "/clear context"
    
    def get_description(self) -> str:
        return "Clear conversation history"
    
    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/clear context"
    
    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        from ..ui.console import get_console, get_prompt_session
        
        console = get_console()
        prompt_session = get_prompt_session()
        
        conversation_history = session.get_conversation_history()
        
        if len(conversation_history) <= 1:
            console.print("[yellow]Context already empty (only system prompt).[/yellow]")
            return CommandResult.success()
            
        file_contexts = sum(1 for msg in conversation_history if msg["role"] == "system" and "User added file" in msg["content"])
        total_messages = len(conversation_history) - 1
        
        console.print(f"[yellow]Current context: {total_messages} messages, {file_contexts} file contexts[/yellow]")
        
        # Confirm with user
        confirm = prompt_session.prompt("🔵 Are you sure you want to clear the context? (y/N): ", default="n").strip().lower()
        
        if confirm in ["y", "yes"]:
            session.clear_context(keep_system_prompt=True)
            console.print("[bold green]✓[/bold green] Context cleared (system prompt retained)")
            return CommandResult.success()
        else:
            console.print("[yellow]Context clear cancelled.[/yellow]")
            return CommandResult.success()


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