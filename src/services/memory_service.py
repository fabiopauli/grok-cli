#!/usr/bin/env python3

"""
Memory Service - Business logic for memory operations

Extracts memory management business logic from MemoryCommand,
providing a clean, testable service layer.
"""

from pathlib import Path
from typing import Any

from ..core.memory_manager import MemoryManager
from ..utils.logging_config import get_logger
from .dtos import (
    MemoryClearResult,
    MemoryListResult,
    MemoryRemoveResult,
    MemorySaveResult,
)


class MemoryService:
    """Pure business logic for memory operations."""

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize MemoryService.

        Args:
            memory_manager: The memory manager instance to wrap
        """
        self.memory_manager = memory_manager
        self.logger = get_logger("services.memory")

    def list_all_memories(self) -> MemoryListResult:
        """
        List all memories (global + directory).

        Returns:
            MemoryListResult with all memories
        """
        memories = self.memory_manager.get_all_memories()
        return MemoryListResult(memories=memories, total_count=len(memories), scope="all")

    def list_global_memories(self) -> MemoryListResult:
        """
        List global memories only.

        Returns:
            MemoryListResult with global memories
        """
        memories = self.memory_manager.get_global_memories()
        return MemoryListResult(memories=memories, total_count=len(memories), scope="global")

    def list_directory_memories(self, directory: Path | None = None) -> MemoryListResult:
        """
        List directory memories only.

        Args:
            directory: Optional directory path (uses current if None)

        Returns:
            MemoryListResult with directory memories
        """
        memories = self.memory_manager.get_directory_memories(directory)
        return MemoryListResult(memories=memories, total_count=len(memories), scope="directory")

    def save_memory(self, content: str, memory_type: str, scope: str) -> MemorySaveResult:
        """
        Save a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory (user_preference, architectural_decision, etc.)
            scope: Scope (global or directory)

        Returns:
            MemorySaveResult with success status and memory ID
        """
        try:
            memory_id = self.memory_manager.save_memory(content, memory_type, scope)
            return MemorySaveResult(success=True, memory_id=memory_id, error=None)
        except Exception as e:
            return MemorySaveResult(success=False, memory_id=None, error=str(e))

    def remove_memory(self, memory_id: str) -> MemoryRemoveResult:
        """
        Remove a memory by ID.

        Args:
            memory_id: ID of memory to remove

        Returns:
            MemoryRemoveResult with success status
        """
        found = self.memory_manager.remove_memory(memory_id)
        return MemoryRemoveResult(success=found, memory_id=memory_id, found=found)

    def clear_directory_memories(self, directory: Path | None = None) -> MemoryClearResult:
        """
        Clear directory memories.

        Args:
            directory: Optional directory path (uses current if None)

        Returns:
            MemoryClearResult with count of cleared memories
        """
        cleared_count = self.memory_manager.clear_directory_memories(directory)
        return MemoryClearResult(cleared_count=cleared_count, scope="directory")

    def clear_global_memories(self) -> MemoryClearResult:
        """
        Clear global memories.

        Returns:
            MemoryClearResult with count of cleared memories
        """
        cleared_count = self.memory_manager.clear_global_memories()
        return MemoryClearResult(cleared_count=cleared_count, scope="global")

    def clear_all_memories(self) -> MemoryClearResult:
        """
        Clear all memories (directory + global).

        Returns:
            MemoryClearResult with total count of cleared memories
        """
        dir_cleared = self.memory_manager.clear_directory_memories()
        global_cleared = self.memory_manager.clear_global_memories()
        total_cleared = dir_cleared + global_cleared
        return MemoryClearResult(cleared_count=total_cleared, scope="all")

    def get_statistics(self) -> dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory statistics
        """
        return self.memory_manager.get_memory_statistics()

    def export_memories(
        self, include_global: bool = True, include_directory: bool = True
    ) -> dict[str, Any]:
        """
        Export memories to dictionary.

        Args:
            include_global: Whether to include global memories
            include_directory: Whether to include directory memories

        Returns:
            Dictionary with exported memories
        """
        return self.memory_manager.export_memories(
            include_global=include_global, include_directory=include_directory
        )

    def import_memories(self, import_data: dict[str, Any], merge: bool = True) -> dict[str, int]:
        """
        Import memories from dictionary.

        Args:
            import_data: Dictionary with memories to import
            merge: Whether to merge with existing or replace

        Returns:
            Dictionary with import statistics
        """
        return self.memory_manager.import_memories(import_data, merge=merge)

    def has_directory_memories(self, directory: Path) -> bool:
        """
        Check if a directory has memories.

        Args:
            directory: Directory path to check

        Returns:
            True if directory has memories
        """
        return self.memory_manager.has_directory_memories(directory)
