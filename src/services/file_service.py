#!/usr/bin/env python3

"""
File Service - Business logic for file operations

Extracts file handling business logic from file commands,
providing a clean, testable service layer.
"""

from pathlib import Path

from ..core.config import Config
from ..utils.file_utils import find_best_matching_file
from ..utils.path_utils import normalize_path
from .dtos import FileResolveResult, ReadResult


class FileService:
    """Pure business logic for file operations."""

    def __init__(self, config: Config):
        """
        Initialize FileService.

        Args:
            config: Configuration instance
        """
        self.config = config

    def resolve_path(self, path_str: str, allow_fuzzy: bool = False) -> FileResolveResult:
        """
        Resolve a path string to an actual file path.

        Args:
            path_str: Path string to resolve
            allow_fuzzy: Whether to allow fuzzy matching if exact path not found

        Returns:
            FileResolveResult with resolved path or error
        """
        try:
            # Try direct normalization first
            normalized = normalize_path(path_str, self.config)
            p = Path(normalized)

            if p.exists():
                return FileResolveResult(
                    success=True,
                    resolved_path=str(p),
                    original_path=path_str,
                    error=None,
                    was_fuzzy_match=False,
                )

            # If not found and fuzzy matching allowed, try fuzzy match
            if allow_fuzzy:
                fuzzy_match = find_best_matching_file(self.config.base_dir, path_str, self.config)
                if fuzzy_match:
                    return FileResolveResult(
                        success=True,
                        resolved_path=fuzzy_match,
                        original_path=path_str,
                        error=None,
                        was_fuzzy_match=True,
                    )

            # Path not found
            return FileResolveResult(
                success=False,
                resolved_path=None,
                original_path=path_str,
                error=f"Path not found: {path_str}",
                was_fuzzy_match=False,
            )

        except Exception as e:
            return FileResolveResult(
                success=False,
                resolved_path=None,
                original_path=path_str,
                error=str(e),
                was_fuzzy_match=False,
            )

    def read_file(self, path: Path) -> ReadResult:
        """
        Read file content.

        Args:
            path: Path to file

        Returns:
            ReadResult with file content or error
        """
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            return ReadResult(success=True, content=content, error=None, path=str(path))
        except Exception as e:
            return ReadResult(success=False, content=None, error=str(e), path=str(path))

    def scan_directory(self, directory: Path) -> tuple[list[Path], list[str]]:
        """
        Scan a directory for files, respecting exclusions.

        Args:
            directory: Directory to scan

        Returns:
            Tuple of (file_paths, warnings)
        """
        file_paths = []
        warnings = []

        try:
            if not directory.exists():
                warnings.append(f"Directory does not exist: {directory}")
                return file_paths, warnings

            if not directory.is_dir():
                warnings.append(f"Not a directory: {directory}")
                return file_paths, warnings

            # Walk directory
            for root, dirs, files in directory.walk():
                # Filter excluded directories (modify in-place)
                dirs[:] = [d for d in dirs if d not in self.config.excluded_files]

                # Process files
                for file in files:
                    if file in self.config.excluded_files:
                        continue

                    file_path = root / file
                    if file_path.suffix.lower() in self.config.excluded_extensions:
                        continue

                    file_paths.append(file_path)

                    # Check file count limit
                    if len(file_paths) >= self.config.max_files_in_add_dir:
                        warnings.append(
                            f"Reached maximum file limit ({self.config.max_files_in_add_dir})"
                        )
                        return file_paths, warnings

        except Exception as e:
            warnings.append(f"Error scanning directory: {str(e)}")

        return file_paths, warnings

    def validate_path_in_project(self, path: Path) -> tuple[bool, str | None]:
        """
        Validate that a path is within the project directory.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            resolved = path.resolve()
            base_dir_resolved = self.config.base_dir.resolve()

            if not str(resolved).startswith(str(base_dir_resolved)):
                return False, f"Path is outside project directory: {path}"

            return True, None

        except Exception as e:
            return False, f"Error validating path: {str(e)}"

    def validate_python_syntax(self, content: str) -> tuple[bool, str | None]:
        """
        Validate Python syntax without executing code.

        Args:
            content: Python source code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        from ..utils.code_inspector import validate_python_syntax

        return validate_python_syntax(content)
