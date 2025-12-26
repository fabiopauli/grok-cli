#!/usr/bin/env python3

"""
Protocol interfaces for Grok Assistant

Defines protocol (structural) types to break circular dependencies
and enable better testing through duck typing.
"""

from pathlib import Path
from typing import Any, Protocol


class ConsoleProtocol(Protocol):
    """Protocol for console output operations."""

    def print(self, *args, **kwargs) -> None:
        """Print output to console."""
        ...

    def clear(self) -> None:
        """Clear the console screen."""
        ...


class PromptProtocol(Protocol):
    """Protocol for user input operations."""

    def prompt(self, message: str, **kwargs) -> str:
        """Prompt user for input."""
        ...


class MemoryManagerProtocol(Protocol):
    """Protocol for memory management operations."""

    def save_memory(self, content: str, memory_type: str, scope: str = "directory") -> str:
        """Save a new memory and return its ID."""
        ...

    def remove_memory(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        ...

    def get_global_memories(self) -> list[dict[str, Any]]:
        """Get all global memories."""
        ...

    def get_directory_memories(self, directory: Path | None = None) -> list[dict[str, Any]]:
        """Get memories for a specific directory."""
        ...

    def get_all_memories(self) -> list[dict[str, Any]]:
        """Get all memories (global + current directory)."""
        ...

    def get_memories_for_context(self) -> list[dict[str, Any]]:
        """Get memories formatted for API context."""
        ...

    def has_directory_memories(self, directory: Path) -> bool:
        """Check if directory has memories."""
        ...

    def clear_directory_memories(self, directory: Path | None = None) -> int:
        """Clear directory memories and return count."""
        ...

    def clear_global_memories(self) -> int:
        """Clear global memories and return count."""
        ...

    def export_memories(
        self, include_global: bool = True, include_directory: bool = True
    ) -> dict[str, Any]:
        """Export memories to dict."""
        ...

    def import_memories(self, import_data: dict[str, Any], merge: bool = True) -> dict[str, int]:
        """Import memories from dict."""
        ...

    def get_memory_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        ...


class ContextManagerProtocol(Protocol):
    """Protocol for context management operations."""

    def mount_file(self, path: str, content: str) -> None:
        """Mount a file to the context."""
        ...

    def add_system_message(self, content: str) -> None:
        """Add a system message to the context."""
        ...

    def add_assistant_message(
        self, content: str, tool_calls: list[dict[str, Any]] | None = None
    ) -> None:
        """Add an assistant message to the context."""
        ...

    def add_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """Add a tool call to the context."""
        ...

    def add_tool_response(self, tool_name: str, result: str) -> None:
        """Add a tool response to the context."""
        ...

    def get_context_for_api(self) -> list[dict[str, Any]]:
        """Get context formatted for API."""
        ...

    def get_context_stats(self) -> dict[str, Any]:
        """Get context statistics."""
        ...

    def clear_context(self, keep_memories: bool = True, keep_mounted_files: bool = False) -> None:
        """Clear the context."""
        ...
