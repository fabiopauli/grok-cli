#!/usr/bin/env python3

"""
UI Adapter Pattern for Grok Assistant

Provides abstraction over UI implementation, enabling:
- Testing without actual console
- Future alternative UIs (web, API, etc.)
- Dependency injection instead of global singletons
"""

from typing import Protocol

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.table import Table


class UIProtocol(Protocol):
    """Protocol defining UI operations."""

    def show_info(self, message: str) -> None:
        """Display informational message."""
        ...

    def show_error(self, message: str) -> None:
        """Display error message."""
        ...

    def show_success(self, message: str) -> None:
        """Display success message."""
        ...

    def show_warning(self, message: str) -> None:
        """Display warning message."""
        ...

    def show_table(self, table: Table) -> None:
        """Display a table."""
        ...

    def print(self, *args, **kwargs) -> None:
        """Print raw output (for compatibility)."""
        ...

    def clear(self) -> None:
        """Clear the screen."""
        ...

    def prompt(self, message: str, default: str = "") -> str:
        """Prompt user for input."""
        ...


class RichUIAdapter:
    """Adapter for Rich console - current production implementation."""

    def __init__(self, console: Console, prompt_session: PromptSession):
        """
        Initialize RichUIAdapter.

        Args:
            console: Rich console instance
            prompt_session: Prompt toolkit session instance
        """
        self.console = console
        self.prompt_session = prompt_session

    def show_info(self, message: str) -> None:
        """Display informational message."""
        self.console.print(f"[bold blue]ℹ[/bold blue] {message}")

    def show_error(self, message: str) -> None:
        """Display error message."""
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def show_success(self, message: str) -> None:
        """Display success message."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def show_warning(self, message: str) -> None:
        """Display warning message."""
        self.console.print(f"[bold yellow]⚠[/bold yellow] {message}")

    def show_table(self, table: Table) -> None:
        """Display a table."""
        self.console.print(table)

    def print(self, *args, **kwargs) -> None:
        """Print raw output (delegates to console)."""
        self.console.print(*args, **kwargs)

    def clear(self) -> None:
        """Clear the screen."""
        self.console.clear()

    def prompt(self, message: str, default: str = "") -> str:
        """
        Prompt user for input.

        Args:
            message: Prompt message
            default: Default value

        Returns:
            User input string
        """
        return self.prompt_session.prompt(message, default=default).strip()


class MockUIAdapter:
    """Mock UI adapter for testing."""

    def __init__(self):
        """Initialize mock UI adapter."""
        self.messages: list[tuple[str, str]] = []
        self.responses: list[str] = []
        self.tables: list[Table] = []
        self.prints: list[str] = []
        self.cleared: bool = False

    def show_info(self, message: str) -> None:
        """Record info message."""
        self.messages.append(("info", message))

    def show_error(self, message: str) -> None:
        """Record error message."""
        self.messages.append(("error", message))

    def show_success(self, message: str) -> None:
        """Record success message."""
        self.messages.append(("success", message))

    def show_warning(self, message: str) -> None:
        """Record warning message."""
        self.messages.append(("warning", message))

    def show_table(self, table: Table) -> None:
        """Record table."""
        self.tables.append(table)

    def print(self, *args, **kwargs) -> None:
        """Record print output."""
        self.prints.append(str(args))

    def clear(self) -> None:
        """Record clear action."""
        self.cleared = True

    def prompt(self, message: str, default: str = "") -> str:
        """
        Return pre-configured response or default.

        Args:
            message: Prompt message (recorded but not used)
            default: Default value

        Returns:
            Next queued response or default
        """
        self.messages.append(("prompt", message))
        if self.responses:
            return self.responses.pop(0)
        return default

    def set_responses(self, responses: list[str]) -> None:
        """
        Set responses for future prompts.

        Args:
            responses: List of responses to return in order
        """
        self.responses = responses.copy()

    def get_messages_by_type(self, message_type: str) -> list[str]:
        """
        Get all messages of a specific type.

        Args:
            message_type: Type of message (info, error, success, warning, prompt)

        Returns:
            List of messages of that type
        """
        return [msg for msg_type, msg in self.messages if msg_type == message_type]

    def clear_history(self) -> None:
        """Clear all recorded history."""
        self.messages.clear()
        self.responses.clear()
        self.tables.clear()
        self.prints.clear()
        self.cleared = False
