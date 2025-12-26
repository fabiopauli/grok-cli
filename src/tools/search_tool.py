#!/usr/bin/env python3

"""
Code Search Tool for Grok Assistant

Provides pattern-based codebase search capabilities using regex.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from ..core.config import Config


class GrepCodebaseTool(BaseTool):
    """Handle grep_codebase function calls for pattern-based search."""

    def get_name(self) -> str:
        return "grep_codebase"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute grep_codebase to search for patterns across files.

        Args:
            pattern: Regex pattern to search for
            file_pattern: Glob pattern for files to search (default: **/*.py)
            case_sensitive: Whether search is case-sensitive (default: False)
            max_results: Maximum number of matches to return (default: 100)

        Returns:
            ToolResult with matches or error
        """
        try:
            pattern = args["pattern"]
            file_pattern = args.get("file_pattern", "**/*.py")
            case_sensitive = args.get("case_sensitive", False)
            max_results = args.get("max_results", 100)

            # Compile regex pattern
            regex_flags = 0 if case_sensitive else re.IGNORECASE
            try:
                compiled_pattern = re.compile(pattern, regex_flags)
            except re.error as e:
                return ToolResult.fail(f"Invalid regex pattern: {e}")

            # Find all matching files
            base_path = Path(self.config.base_dir)
            try:
                matching_files = list(base_path.glob(file_pattern))
            except Exception as e:
                return ToolResult.fail(f"Invalid file pattern '{file_pattern}': {e}")

            if not matching_files:
                return ToolResult.ok(
                    f"No files found matching pattern '{file_pattern}' in {base_path}"
                )

            # Search through files
            matches = []
            total_files_searched = 0
            files_with_matches = 0

            for file_path in matching_files:
                # Skip directories and excluded files
                if not file_path.is_file():
                    continue

                if file_path.name in self.config.excluded_files:
                    continue

                if file_path.suffix in self.config.excluded_extensions:
                    continue

                total_files_searched += 1

                # Read and search file
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    file_matches = []
                    for line_num, line in enumerate(lines, start=1):
                        if compiled_pattern.search(line):
                            file_matches.append(
                                {
                                    "line_number": line_num,
                                    "line": line.rstrip(),
                                }
                            )

                            # Stop if we've hit max results
                            if len(matches) + len(file_matches) >= max_results:
                                break

                    if file_matches:
                        files_with_matches += 1
                        # Get relative path for cleaner output
                        try:
                            relative_path = file_path.relative_to(base_path)
                        except ValueError:
                            relative_path = file_path

                        matches.append(
                            {
                                "file": str(relative_path),
                                "matches": file_matches,
                            }
                        )

                    # Stop if we've hit max results
                    if len(matches) >= max_results:
                        break

                except (UnicodeDecodeError, PermissionError):
                    # Skip files we can't read
                    continue

            # Format results
            if not matches:
                return ToolResult.ok(
                    f"Pattern '{pattern}' not found in {total_files_searched} files matching '{file_pattern}'"
                )

            # Build response
            response_lines = [
                f"Found {sum(len(m['matches']) for m in matches)} matches in {files_with_matches} files "
                f"(searched {total_files_searched} files matching '{file_pattern}'):\n"
            ]

            for file_match in matches:
                file_path = file_match["file"]
                response_lines.append(f"\n📁 {file_path}")

                for match in file_match["matches"]:
                    line_num = match["line_number"]
                    line = match["line"]
                    # Highlight the matched pattern in the line
                    highlighted_line = compiled_pattern.sub(
                        lambda m: f">>>{m.group()}<<<", line
                    )
                    response_lines.append(f"  {line_num}: {highlighted_line}")

            return ToolResult.ok("\n".join(response_lines))

        except KeyError as e:
            return ToolResult.fail(f"Missing required argument: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error during search: {str(e)}")


def create_search_tools(config: Config) -> List[BaseTool]:
    """Create all search tools."""
    return [GrepCodebaseTool(config)]
