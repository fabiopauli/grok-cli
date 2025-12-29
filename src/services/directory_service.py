#!/usr/bin/env python3

"""
Directory Service - Business logic for directory operations

Extracts directory change logic from FolderCommand, providing a clean,
testable service layer for directory operations.
"""

from pathlib import Path
from typing import Optional

from ..core.config import Config
from .dtos import DirectoryChangeResult


class DirectoryService:
    """Pure business logic for directory operations."""

    def __init__(self, config: Config):
        """
        Initialize DirectoryService.

        Args:
            config: Configuration instance
        """
        self.config = config

    def resolve_directory_path(self, path_str: str) -> Path:
        """
        Resolve a directory path string to an absolute Path.

        Args:
            path_str: Path string to resolve (can be relative, absolute, or use ~)

        Returns:
            Resolved absolute Path

        Raises:
            ValueError: If path is invalid
        """
        try:
            # Handle special cases
            if path_str == "..":
                return self.config.base_dir.parent
            elif path_str == ".":
                return self.config.base_dir
            elif path_str.startswith("~"):
                return Path(path_str).expanduser().resolve()
            elif Path(path_str).is_absolute():
                return Path(path_str).resolve()
            else:
                # Relative to current directory
                return (self.config.base_dir / path_str).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {str(e)}")

    def validate_directory(self, path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate that a path exists and is a directory.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not path.exists():
                return False, f"Directory does not exist: {path}"

            if not path.is_dir():
                return False, f"Path is not a directory: {path}"

            return True, None

        except (FileNotFoundError, OSError, PermissionError) as e:
            return False, f"Error accessing directory: {str(e)}"

    def change_directory(
        self,
        new_path: Path,
        session: Optional[object] = None
    ) -> DirectoryChangeResult:
        """
        Change the working directory.

        Args:
            new_path: New directory path (already resolved and validated)
            session: Optional GrokSession for memory integration

        Returns:
            DirectoryChangeResult with success status and details
        """
        old_path = self.config.base_dir

        # Update config
        self.config.base_dir = new_path

        # Handle memory integration if session provided
        memory_info = None
        if session and hasattr(session, 'update_working_directory'):
            memory_info = session.update_working_directory(new_path)

        return DirectoryChangeResult(
            success=True,
            old_path=str(old_path),
            new_path=str(new_path),
            memory_info=memory_info,
            error=None
        )
