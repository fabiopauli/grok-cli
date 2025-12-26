#!/usr/bin/env python3

"""
Directory-Aware Memory Manager for Grok Assistant

Manages persistent memories with global and directory-specific storage.
Handles memory loading, saving, and switching when directories change.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..utils.logging_config import get_logger
from .config import Config


class MemoryManager:
    """
    Manages persistent memories with directory-aware storage.

    Provides global memories that persist across all directories and
    directory-specific memories that are loaded based on current working directory.
    """

    def __init__(self, config: Config):
        """
        Initialize the memory manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger("memory")
        self.current_directory = config.base_dir

        # Memory storage
        self.global_memories: list[dict[str, Any]] = []
        self.directory_memories: dict[str, list[dict[str, Any]]] = {}

        # File paths
        self.global_memory_file = Path.home() / ".grok_global_memory.json"

        # Load initial memories
        self.logger.debug("MemoryManager initializing")
        self._load_global_memories()
        self._load_directory_memories(self.current_directory)
        self.logger.info(
            f"MemoryManager initialized: {len(self.global_memories)} global memories, directory={self.current_directory}"
        )

    def save_memory(self, content: str, memory_type: str, scope: str = "directory") -> str:
        """
        Save a new memory.

        Args:
            content: Memory content
            memory_type: Type of memory (user_preference, architectural_decision, etc.)
            scope: Memory scope (directory or global)

        Returns:
            Memory ID of the saved memory
        """
        memory_id = f"mem_{uuid.uuid4().hex[:8]}"

        memory = {
            "id": memory_id,
            "type": memory_type,
            "content": content,
            "created": datetime.now().isoformat(),
            "scope": scope,
        }

        if scope == "global":
            # Save to global memories
            self.global_memories.append(memory)
            self._save_global_memories()
        else:
            # Save to current directory memories
            current_dir_str = str(self.current_directory)
            if current_dir_str not in self.directory_memories:
                self.directory_memories[current_dir_str] = []

            self.directory_memories[current_dir_str].append(memory)
            self._save_directory_memories(self.current_directory)

        return memory_id

    def remove_memory(self, memory_id: str) -> bool:
        """
        Remove a memory by ID.

        Args:
            memory_id: ID of the memory to remove

        Returns:
            True if memory was found and removed, False otherwise
        """
        # Try to remove from global memories
        for i, memory in enumerate(self.global_memories):
            if memory["id"] == memory_id:
                del self.global_memories[i]
                self._save_global_memories()
                return True

        # Try to remove from current directory memories
        current_dir_str = str(self.current_directory)
        if current_dir_str in self.directory_memories:
            for i, memory in enumerate(self.directory_memories[current_dir_str]):
                if memory["id"] == memory_id:
                    del self.directory_memories[current_dir_str][i]
                    self._save_directory_memories(self.current_directory)
                    return True

        return False

    def get_global_memories(self) -> list[dict[str, Any]]:
        """Get all global memories."""
        return self.global_memories.copy()

    def get_directory_memories(self, directory: Path | None = None) -> list[dict[str, Any]]:
        """
        Get memories for a specific directory.

        Args:
            directory: Directory to get memories for (current directory if None)

        Returns:
            List of directory-specific memories
        """
        if directory is None:
            directory = self.current_directory

        dir_str = str(directory)
        return self.directory_memories.get(dir_str, []).copy()

    def get_all_memories(self) -> list[dict[str, Any]]:
        """Get all memories (global + current directory)."""
        all_memories = self.global_memories.copy()
        all_memories.extend(self.get_directory_memories())
        return all_memories

    def get_memories_for_context(self) -> list[dict[str, Any]]:
        """
        Get memories formatted for context injection.

        Returns:
            List of memories to inject into context
        """
        return self.get_all_memories()

    def change_directory(self, new_directory: Path) -> dict[str, Any]:
        """
        Change current directory and load corresponding memories.

        Args:
            new_directory: New directory path

        Returns:
            Dictionary with information about the directory change
        """
        old_directory = self.current_directory
        self.current_directory = new_directory

        # Check if new directory has existing memories
        new_dir_str = str(new_directory)
        has_existing_memories = (
            new_dir_str in self.directory_memories and len(self.directory_memories[new_dir_str]) > 0
        )

        # Load memories for new directory
        self._load_directory_memories(new_directory)

        return {
            "old_directory": str(old_directory),
            "new_directory": str(new_directory),
            "has_existing_memories": has_existing_memories,
            "memory_count": len(self.get_directory_memories()),
            "global_memory_count": len(self.global_memories),
        }

    def initialize_directory_memories(self, directory: Path) -> None:
        """
        Initialize empty memory storage for a directory.

        Args:
            directory: Directory to initialize
        """
        dir_str = str(directory)
        if dir_str not in self.directory_memories:
            self.directory_memories[dir_str] = []
            self._save_directory_memories(directory)

    def has_directory_memories(self, directory: Path) -> bool:
        """
        Check if a directory has existing memories.

        Args:
            directory: Directory to check

        Returns:
            True if directory has memories, False otherwise
        """
        dir_str = str(directory)
        return dir_str in self.directory_memories and len(self.directory_memories[dir_str]) > 0

    def clear_directory_memories(self, directory: Path | None = None) -> int:
        """
        Clear memories for a directory.

        Args:
            directory: Directory to clear (current directory if None)

        Returns:
            Number of memories that were cleared
        """
        if directory is None:
            directory = self.current_directory

        dir_str = str(directory)
        count = len(self.directory_memories.get(dir_str, []))

        if dir_str in self.directory_memories:
            self.directory_memories[dir_str] = []
            self._save_directory_memories(directory)

        return count

    def clear_global_memories(self) -> int:
        """
        Clear all global memories.

        Returns:
            Number of memories that were cleared
        """
        count = len(self.global_memories)
        self.global_memories = []
        self._save_global_memories()
        return count

    def export_memories(
        self, include_global: bool = True, include_directory: bool = True
    ) -> dict[str, Any]:
        """
        Export memories for backup or analysis.

        Args:
            include_global: Whether to include global memories
            include_directory: Whether to include directory memories

        Returns:
            Dictionary containing memory data
        """
        export_data = {
            "export_time": datetime.now().isoformat(),
            "current_directory": str(self.current_directory),
        }

        if include_global:
            export_data["global_memories"] = self.global_memories

        if include_directory:
            export_data["directory_memories"] = self.directory_memories

        return export_data

    def import_memories(self, import_data: dict[str, Any], merge: bool = True) -> dict[str, int]:
        """
        Import memories from exported data.

        Args:
            import_data: Exported memory data
            merge: Whether to merge with existing memories or replace

        Returns:
            Dictionary with import statistics
        """
        stats = {"global_imported": 0, "directory_imported": 0}

        if not merge:
            self.global_memories = []
            self.directory_memories = {}

        # Import global memories
        if "global_memories" in import_data:
            for memory in import_data["global_memories"]:
                if merge:
                    # Check for duplicates
                    if not any(m["id"] == memory["id"] for m in self.global_memories):
                        self.global_memories.append(memory)
                        stats["global_imported"] += 1
                else:
                    self.global_memories.append(memory)
                    stats["global_imported"] += 1

        # Import directory memories
        if "directory_memories" in import_data:
            for dir_path, memories in import_data["directory_memories"].items():
                if merge and dir_path in self.directory_memories:
                    # Merge with existing
                    existing_ids = {m["id"] for m in self.directory_memories[dir_path]}
                    for memory in memories:
                        if memory["id"] not in existing_ids:
                            self.directory_memories[dir_path].append(memory)
                            stats["directory_imported"] += 1
                else:
                    # Replace or add new
                    self.directory_memories[dir_path] = memories
                    stats["directory_imported"] += len(memories)

        # Save imported data
        self._save_global_memories()
        for dir_path in self.directory_memories:
            self._save_directory_memories(Path(dir_path))

        return stats

    def _load_global_memories(self) -> None:
        """Load global memories from file."""
        try:
            if self.global_memory_file.exists():
                with open(self.global_memory_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.global_memories = data.get("memories", [])
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            # If file doesn't exist or is corrupted, start with empty memories
            self.global_memories = []

    def _save_global_memories(self) -> None:
        """Save global memories to file."""
        try:
            self.global_memory_file.parent.mkdir(parents=True, exist_ok=True)

            data = {"memories": self.global_memories, "last_updated": datetime.now().isoformat()}

            with open(self.global_memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            # Log error but don't crash
            print(f"Warning: Could not save global memories: {e}")

    def _load_directory_memories(self, directory: Path) -> None:
        """
        Load memories for a specific directory.

        Args:
            directory: Directory to load memories for
        """
        dir_str = str(directory)
        memory_file = directory / ".grok_memory.json"

        try:
            if memory_file.exists():
                with open(memory_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.directory_memories[dir_str] = data.get("memories", [])
            else:
                self.directory_memories[dir_str] = []
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            # If file doesn't exist or is corrupted, start with empty memories
            self.directory_memories[dir_str] = []

    def _save_directory_memories(self, directory: Path) -> None:
        """
        Save memories for a specific directory.

        Args:
            directory: Directory to save memories for
        """
        dir_str = str(directory)
        memory_file = directory / ".grok_memory.json"

        try:
            memories = self.directory_memories.get(dir_str, [])

            data = {
                "directory": dir_str,
                "memories": memories,
                "last_updated": datetime.now().isoformat(),
            }

            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            # Log error but don't crash
            print(f"Warning: Could not save directory memories for {directory}: {e}")

    def get_memory_statistics(self) -> dict[str, Any]:
        """
        Get statistics about memory usage.

        Returns:
            Dictionary with memory statistics
        """
        total_directory_memories = sum(
            len(memories) for memories in self.directory_memories.values()
        )

        # Count memories by type
        type_counts = {}
        for memory in self.get_all_memories():
            memory_type = memory.get("type", "unknown")
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1

        return {
            "global_memories": len(self.global_memories),
            "current_directory_memories": len(self.get_directory_memories()),
            "total_directory_memories": total_directory_memories,
            "total_directories_with_memories": len(self.directory_memories),
            "current_directory": str(self.current_directory),
            "memory_types": type_counts,
            "total_memories": len(self.global_memories) + total_directory_memories,
        }
