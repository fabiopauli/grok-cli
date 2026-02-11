#!/usr/bin/env python3

"""
Code Inspector - Lightweight AST-based Python code analysis

Provides structural analysis of Python files without heavy complexity metrics.
"""

import ast
from pathlib import Path
from typing import Any


class CodeInspector:
    """Lightweight Python code inspector using AST."""

    @staticmethod
    def inspect_file(file_path: str | Path) -> dict[str, Any]:
        """
        Inspect a Python file and extract its structure.

        Args:
            file_path: Path to the Python file

        Returns:
            Dictionary with file structure:
            {
                "success": bool,
                "error": Optional[str],
                "imports": List[Dict],
                "classes": List[Dict],
                "functions": List[Dict],
                "module_docstring": Optional[str]
            }
        """
        try:
            # Read file content
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "imports": [],
                    "classes": [],
                    "functions": [],
                    "module_docstring": None,
                }

            with open(path, encoding="utf-8") as f:
                source = f.read()

            # Parse AST
            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"Syntax error at line {e.lineno}: {e.msg}",
                    "imports": [],
                    "classes": [],
                    "functions": [],
                    "module_docstring": None,
                }

            # Extract module docstring
            module_docstring = ast.get_docstring(tree)

            # Extract components
            imports = CodeInspector._extract_imports(tree)
            classes = CodeInspector._extract_classes(tree)
            functions = CodeInspector._extract_functions(tree)

            return {
                "success": True,
                "error": None,
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "module_docstring": module_docstring,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "imports": [],
                "classes": [],
                "functions": [],
                "module_docstring": None,
            }

    @staticmethod
    def _extract_imports(tree: ast.AST) -> list[dict[str, Any]]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(
                        {
                            "type": "from",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                        }
                    )

        return imports

    @staticmethod
    def _extract_classes(tree: ast.AST) -> list[dict[str, Any]]:
        """Extract class definitions."""
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract base classes
                bases = [ast.unparse(base) for base in node.bases]

                # Extract methods
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(
                            {
                                "name": item.name,
                                "line": item.lineno,
                                "is_async": isinstance(item, ast.AsyncFunctionDef),
                                "docstring": ast.get_docstring(item),
                            }
                        )

                classes.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": bases,
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                    }
                )

        return classes

    @staticmethod
    def _extract_functions(tree: ast.AST) -> list[dict[str, Any]]:
        """Extract top-level function definitions (not methods)."""
        functions = []

        # Only look at module-level nodes
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract argument names
                args = [arg.arg for arg in node.args.args]

                functions.append(
                    {
                        "name": node.name,
                        "line": node.lineno,
                        "args": args,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node),
                    }
                )

        return functions

    @staticmethod
    def validate_syntax(source: str) -> tuple[bool, str | None]:
        """
        Validate Python syntax without executing code.

        Args:
            source: Python source code string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(source)
            return (True, None)
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}, column {e.offset}: {e.msg}"
            if e.text:
                error_msg += f"\n  {e.text.rstrip()}"
                if e.offset:
                    error_msg += f"\n  {' ' * (e.offset - 1)}^"
            return (False, error_msg)
        except Exception as e:
            return (False, f"Unexpected error: {str(e)}")

    @staticmethod
    def format_structure_summary(inspection: dict[str, Any]) -> str:
        """
        Format inspection results into a human-readable summary.

        Args:
            inspection: Results from inspect_file()

        Returns:
            Formatted string summary
        """
        if not inspection["success"]:
            return f"❌ Error: {inspection['error']}"

        lines = []

        # Module docstring
        if inspection["module_docstring"]:
            lines.append("📄 Module:")
            lines.append(f'  """{inspection["module_docstring"]}"""')
            lines.append("")

        # Imports
        if inspection["imports"]:
            lines.append(f"📦 Imports ({len(inspection['imports'])}):")
            for imp in inspection["imports"][:10]:  # Limit to first 10
                if imp["type"] == "import":
                    alias_str = f" as {imp['alias']}" if imp["alias"] else ""
                    lines.append(f"  import {imp['module']}{alias_str}")
                else:
                    alias_str = f" as {imp['alias']}" if imp["alias"] else ""
                    lines.append(f"  from {imp['module']} import {imp['name']}{alias_str}")
            if len(inspection["imports"]) > 10:
                lines.append(f"  ... and {len(inspection['imports']) - 10} more")
            lines.append("")

        # Classes
        if inspection["classes"]:
            lines.append(f"🏛️  Classes ({len(inspection['classes'])}):")
            for cls in inspection["classes"]:
                bases_str = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
                lines.append(f"  class {cls['name']}{bases_str}  # line {cls['line']}")
                if cls["methods"]:
                    for method in cls["methods"][:5]:  # Limit to first 5 methods
                        async_str = "async " if method["is_async"] else ""
                        lines.append(f"    {async_str}def {method['name']}()")
                    if len(cls["methods"]) > 5:
                        lines.append(f"    ... and {len(cls['methods']) - 5} more methods")
            lines.append("")

        # Functions
        if inspection["functions"]:
            lines.append(f"⚙️  Functions ({len(inspection['functions'])}):")
            for func in inspection["functions"]:
                async_str = "async " if func["is_async"] else ""
                args_str = ", ".join(func["args"])
                lines.append(
                    f"  {async_str}def {func['name']}({args_str})  # line {func['line']}"
                )
            lines.append("")

        return "\n".join(lines)


# Convenience function for quick validation
def validate_python_syntax(source: str) -> tuple[bool, str | None]:
    """
    Validate Python syntax.

    Args:
        source: Python source code

    Returns:
        Tuple of (is_valid, error_message)
    """
    return CodeInspector.validate_syntax(source)
