#!/usr/bin/env python3

"""
Editor Tool for Grok Assistant

Provides deterministic search and replace functionality.
"""

from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..utils.editor_utils import search_and_replace, validate_replacement
from ..utils.path_utils import normalize_path


class SearchReplaceFileTool(BaseTool):
    """Handle search_replace_file function calls for precise editing."""

    def get_name(self) -> str:
        """Return the tool name for registration."""
        return "search_replace_file"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute search_replace_file for deterministic code editing.

        Args:
            file_path: Path to file to edit
            search_block: Exact code block to search for
            replace_block: Replacement code block
            strict: If True, fail if not exactly 1 match (default: True)

        Returns:
            ToolResult with success or error
        """
        try:
            file_path = args["file_path"]
            search_block = args["search_block"]
            replace_block = args["replace_block"]
            strict = args.get("strict", True)

            # Normalize path
            try:
                normalized_path = normalize_path(file_path, self.config)
            except Exception as e:
                return ToolResult.fail(f"Invalid file path: {e}")

            # Check if file exists
            path = Path(normalized_path)
            if not path.exists():
                return ToolResult.fail(f"File not found: {normalized_path}")

            # Read file content
            try:
                with open(normalized_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
            except Exception as e:
                return ToolResult.fail(f"Error reading file '{normalized_path}': {e}")

            # Perform search and replace
            success, new_content, match_count, error_msg = search_and_replace(
                original_content, search_block, replace_block, strict=strict
            )

            if not success:
                return ToolResult.fail(
                    f"Search and replace failed for '{normalized_path}': {error_msg}"
                )

            # Validate replacement
            is_valid, validation_error = validate_replacement(
                original_content, new_content, search_block, replace_block
            )

            if not is_valid:
                return ToolResult.fail(
                    f"Replacement validation failed for '{normalized_path}': {validation_error}"
                )

            # For Python files, validate syntax before writing
            if path.suffix in [".py", ".pyw"]:
                from ..utils.code_inspector import validate_python_syntax

                syntax_valid, syntax_error = validate_python_syntax(new_content)
                if not syntax_valid:
                    return ToolResult.fail(
                        f"Replacement would create invalid Python syntax in '{normalized_path}':\n{syntax_error}\n\n"
                        f"The file was NOT modified. Please fix the syntax error in your replacement block and try again."
                    )

            # Write new content
            try:
                with open(normalized_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except Exception as e:
                return ToolResult.fail(f"Error writing file '{normalized_path}': {e}")

            # Build success message
            if match_count == 1:
                return ToolResult.ok(
                    f"Successfully replaced 1 occurrence in '{normalized_path}'"
                )
            else:
                return ToolResult.ok(
                    f"Successfully replaced {match_count} occurrences in '{normalized_path}'"
                )

        except KeyError as e:
            return ToolResult.fail(f"Missing required argument: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error during search and replace: {str(e)}")


class ApplyDiffPatchTool(BaseTool):
    """Handle apply_diff_patch function calls for diff-based editing."""

    def get_name(self) -> str:
        """Return the tool name for registration."""
        return "apply_diff_patch"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Apply a unified diff patch to a file.

        Args:
            file_path: Path to file to patch
            diff: Unified diff string (output of diff -u)

        Returns:
            ToolResult with success or error
        """
        import re
        from pathlib import Path

        try:
            file_path = args["file_path"]
            diff_text = args["diff"]

            # Normalize path
            try:
                normalized_path = normalize_path(file_path, self.config)
            except Exception as e:
                return ToolResult.fail(f"Invalid file path: {e}")

            # Check if file exists
            path = Path(normalized_path)
            if not path.exists():
                return ToolResult.fail(f"File not found: {normalized_path}")

            # Read original content
            try:
                with open(normalized_path, "r", encoding="utf-8") as f:
                    original_lines = f.readlines()
            except Exception as e:
                return ToolResult.fail(f"Error reading file: {e}")

            # Parse and apply unified diff
            try:
                patched_lines = self._apply_unified_diff(original_lines, diff_text)
            except Exception as e:
                return ToolResult.fail(f"Error applying diff: {e}")

            new_content = "".join(patched_lines)

            # Validate Python syntax if applicable
            if path.suffix in [".py", ".pyw"]:
                from ..utils.code_inspector import validate_python_syntax
                syntax_valid, syntax_error = validate_python_syntax(new_content)
                if not syntax_valid:
                    return ToolResult.fail(
                        f"Patch would create invalid Python syntax:\n{syntax_error}\n\n"
                        f"The file was NOT modified."
                    )

            # Write patched content
            try:
                with open(normalized_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except Exception as e:
                return ToolResult.fail(f"Error writing file: {e}")

            return ToolResult.ok(
                f"Successfully applied diff patch to '{normalized_path}'"
            )

        except KeyError as e:
            return ToolResult.fail(f"Missing required argument: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error applying diff patch: {str(e)}")

    def _apply_unified_diff(self, original_lines: List[str], diff_text: str) -> List[str]:
        """
        Apply a unified diff to original lines.

        Args:
            original_lines: Original file lines (with newlines)
            diff_text: Unified diff string

        Returns:
            Patched lines
        """
        import re

        # Parse the diff to extract hunks
        diff_lines = diff_text.strip().split('\n')

        # Skip header lines (---, +++)
        hunk_start = 0
        for i, line in enumerate(diff_lines):
            if line.startswith('@@'):
                hunk_start = i
                break

        # Apply hunks
        result = list(original_lines)
        offset = 0  # Track line number offset from previous hunks

        i = hunk_start
        while i < len(diff_lines):
            line = diff_lines[i]

            if line.startswith('@@'):
                # Parse hunk header: @@ -start,count +start,count @@
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if not match:
                    raise ValueError(f"Invalid hunk header: {line}")

                old_start = int(match.group(1)) - 1  # Convert to 0-indexed
                old_count = int(match.group(2)) if match.group(2) else 1

                # Process hunk lines
                i += 1
                hunk_deletions = []
                hunk_additions = []

                while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                    hunk_line = diff_lines[i]
                    if hunk_line.startswith('-'):
                        hunk_deletions.append(hunk_line[1:])
                    elif hunk_line.startswith('+'):
                        hunk_additions.append(hunk_line[1:] + '\n')
                    elif hunk_line.startswith(' ') or hunk_line == '':
                        # Context line - verify match
                        pass
                    i += 1

                # Apply the hunk
                actual_start = old_start + offset

                # Remove old lines and insert new ones
                del result[actual_start:actual_start + len(hunk_deletions)]
                for j, add_line in enumerate(hunk_additions):
                    result.insert(actual_start + j, add_line)

                # Update offset
                offset += len(hunk_additions) - len(hunk_deletions)
            else:
                i += 1

        return result


def create_editor_tools(config: Config) -> List[BaseTool]:
    """Create all editor tools."""
    return [
        SearchReplaceFileTool(config),
        ApplyDiffPatchTool(config),
    ]
