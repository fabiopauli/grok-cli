#!/usr/bin/env python3

"""
Code Inspector Tool for Grok Assistant

Provides on-demand AST-based code structure inspection.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..utils.code_inspector import CodeInspector
from ..utils.path_utils import normalize_path


class InspectCodeStructureTool(BaseTool):
    """Handle inspect_code_structure function calls for AST-based code analysis."""

    def get_name(self) -> str:
        return "inspect_code_structure"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute inspect_code_structure to analyze Python file structure.

        Args:
            file_path: Path to Python file to inspect
            include_docstrings: Whether to include docstrings in output (default: True)
            format: Output format - 'json' or 'summary' (default: 'summary')

        Returns:
            ToolResult with file structure or error
        """
        try:
            file_path = args["file_path"]
            include_docstrings = args.get("include_docstrings", True)
            output_format = args.get("format", "summary")

            # Normalize path
            try:
                normalized_path = normalize_path(file_path, self.config)
            except Exception as e:
                return ToolResult.fail(f"Invalid file path: {e}")

            # Check if file exists and is Python
            path = Path(normalized_path)
            if not path.exists():
                return ToolResult.fail(f"File not found: {normalized_path}")

            if path.suffix not in [".py", ".pyw"]:
                return ToolResult.fail(
                    f"Not a Python file: {normalized_path} (extension: {path.suffix}). "
                    "This tool only works with .py and .pyw files."
                )

            # Inspect the file
            inspection = CodeInspector.inspect_file(normalized_path)

            if not inspection["success"]:
                return ToolResult.fail(
                    f"Failed to inspect file '{normalized_path}': {inspection['error']}"
                )

            # Strip docstrings if requested
            if not include_docstrings:
                inspection = self._remove_docstrings(inspection)

            # Format output
            if output_format == "json":
                # Return JSON representation
                return ToolResult.ok(json.dumps(inspection, indent=2))
            else:
                # Return human-readable summary
                summary = CodeInspector.format_structure_summary(inspection)
                return ToolResult.ok(
                    f"Structure of '{normalized_path}':\n\n{summary}"
                )

        except KeyError as e:
            return ToolResult.fail(f"Missing required argument: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error inspecting file: {str(e)}")

    @staticmethod
    def _remove_docstrings(inspection: Dict[str, Any]) -> Dict[str, Any]:
        """Remove docstrings from inspection results."""
        inspection = inspection.copy()
        inspection["module_docstring"] = None

        for cls in inspection.get("classes", []):
            cls["docstring"] = None
            for method in cls.get("methods", []):
                method["docstring"] = None

        for func in inspection.get("functions", []):
            func["docstring"] = None

        return inspection


def create_inspector_tools(config: Config) -> List[BaseTool]:
    """Create all code inspector tools."""
    return [InspectCodeStructureTool(config)]
