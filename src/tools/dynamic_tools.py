#!/usr/bin/env python3

"""
Dynamic Tool System for Grok Assistant

Provides:
1. CreateToolTool - AI-facing tool for creating new tools
2. DynamicToolLoader - Runtime loading of custom tools
3. ToolValidator - Safety validation for custom tools
"""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..utils.code_inspector import CodeInspector


# Dangerous modules/functions to block
BLOCKED_IMPORTS = {
    'subprocess', 'os.system', 'os.popen', 'os.spawn',
    'eval', 'exec', 'compile', '__import__',
    'pickle', 'shelve', 'marshal',
    'ctypes', 'cffi',
}

BLOCKED_CALLS = {
    'eval', 'exec', 'compile', '__import__',
    'breakpoint',
}


class ToolValidator:
    """Validates custom tool code for safety."""

    @staticmethod
    def validate_tool_code(source: str) -> tuple[bool, str]:
        """
        Validate tool source code for safety and correctness.

        Args:
            source: Python source code

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Step 1: Syntax validation
        is_valid, syntax_error = CodeInspector.validate_syntax(source)
        if not is_valid:
            return False, f"Syntax error: {syntax_error}"

        # Step 2: Parse AST for dangerous patterns
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return False, f"Parse error: {e}"

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BLOCKED_IMPORTS:
                        return False, f"Blocked import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                full_name = f"{module}.{node.names[0].name}" if node.names else module
                if module in BLOCKED_IMPORTS or full_name in BLOCKED_IMPORTS:
                    return False, f"Blocked import: {module}"
            elif isinstance(node, ast.Call):
                # Check function calls
                if isinstance(node.func, ast.Name):
                    if node.func.id in BLOCKED_CALLS:
                        return False, f"Blocked function call: {node.func.id}"
                # Check attribute calls like os.system()
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        call_name = f"{node.func.value.id}.{node.func.attr}"
                        if call_name == 'os.system' or call_name == 'os.popen':
                            return False, f"Blocked function call: {call_name}"

        # Step 3: Check for required structure using AST
        # Parse source to inspect structure
        tree = ast.parse(source)

        # Must have a class that inherits from BaseTool
        has_tool_class = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseTool
                base_names = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_names.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_names.append(base.attr)

                if 'BaseTool' in base_names:
                    has_tool_class = True
                    # Check required methods
                    method_names = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_names.append(item.name)

                    if 'get_name' not in method_names:
                        return False, f"Tool class {node.name} missing get_name() method"
                    if 'execute' not in method_names:
                        return False, f"Tool class {node.name} missing execute() method"

        if not has_tool_class:
            return False, "No class inheriting from BaseTool found"

        # Step 4: Check for create_tool factory function
        has_factory = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'create_tool':
                has_factory = True
                break

        if not has_factory:
            return False, "Missing create_tool(config) factory function"

        return True, ""

    @staticmethod
    def inspect_file_content(source: str) -> Dict[str, Any]:
        """Helper to inspect source code content."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {"success": False, "classes": [], "functions": []}

        classes = []
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(base) for base in node.bases]
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({"name": item.name})
                classes.append({"name": node.name, "bases": bases, "methods": methods})
            elif isinstance(node, ast.FunctionDef):
                # Only top-level functions
                if isinstance(node, ast.FunctionDef) and not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                    functions.append({"name": node.name})

        # Add top-level functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({"name": node.name})

        return {"success": True, "classes": classes, "functions": functions}

    @staticmethod
    def validate_tool_schema(schema: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate a tool schema definition.

        Args:
            schema: Tool schema dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ['name', 'description', 'parameters']
        for field in required_fields:
            if field not in schema:
                return False, f"Missing required field: {field}"

        if not isinstance(schema['name'], str) or not schema['name']:
            return False, "Tool name must be a non-empty string"

        if not isinstance(schema['description'], str):
            return False, "Tool description must be a string"

        params = schema.get('parameters', {})
        if not isinstance(params, dict):
            return False, "Parameters must be a dictionary"

        if params.get('type') != 'object':
            return False, "Parameters type must be 'object'"

        return True, ""


class DynamicToolLoader:
    """
    Loads and manages custom tools from the filesystem.

    Can optionally register tools into a central ToolRegistry to maintain
    a single source of truth for available capabilities.
    """

    def __init__(self, config: Config, registry=None):
        """
        Initialize the dynamic tool loader.

        Args:
            config: Configuration object
            registry: Optional ToolRegistry instance for centralized registration.
                      If provided, all loaded tools will be registered into it.
        """
        self.config = config
        self._registry = registry  # Central registry for single source of truth
        self._loaded_tools: Dict[str, BaseTool] = {}
        self._tool_schemas: Dict[str, Dict[str, Any]] = {}

        # Use config's custom_tools_dir if set, otherwise use default
        if hasattr(config, 'custom_tools_dir') and config.custom_tools_dir:
            self.CUSTOM_TOOLS_DIR = Path(config.custom_tools_dir)
        else:
            self.CUSTOM_TOOLS_DIR = Path.home() / ".grok" / "custom_tools"

        # Ensure directory exists
        self.ensure_tools_directory()

    def set_registry(self, registry) -> None:
        """
        Set the central tool registry.

        When a registry is set, newly loaded tools will be registered into it
        rather than just stored locally.

        Args:
            registry: ToolRegistry instance
        """
        self._registry = registry

    def ensure_tools_directory(self) -> Path:
        """Ensure the custom tools directory exists."""
        self.CUSTOM_TOOLS_DIR.mkdir(parents=True, exist_ok=True)

        # Create __init__.py if needed
        init_file = self.CUSTOM_TOOLS_DIR / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Custom tools for Grok Assistant."""\n')

        return self.CUSTOM_TOOLS_DIR

    def load_all_tools(self) -> List[BaseTool]:
        """
        Load all custom tools from the custom_tools directory.

        Returns:
            List of loaded tool instances
        """
        self.ensure_tools_directory()
        loaded = []

        for tool_file in self.CUSTOM_TOOLS_DIR.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            try:
                tool = self._load_tool_from_file(tool_file)
                if tool:
                    loaded.append(tool)
            except Exception as e:
                # Log but don't crash on individual tool failures
                print(f"Warning: Failed to load tool from {tool_file}: {e}")

        return loaded

    def _load_tool_from_file(self, tool_file: Path) -> Optional[BaseTool]:
        """
        Load a single tool from a Python file.

        If a ToolRegistry is set, the tool will be registered into it.
        Otherwise, it's stored locally in this loader.

        Args:
            tool_file: Path to the tool file

        Returns:
            Tool instance or None if loading failed
        """
        # Read and validate source
        source = tool_file.read_text()
        is_valid, error = ToolValidator.validate_tool_code(source)
        if not is_valid:
            raise ValueError(f"Invalid tool code: {error}")

        # Load module
        spec = importlib.util.spec_from_file_location(
            f"custom_tool_{tool_file.stem}",
            tool_file
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {tool_file}")

        module = importlib.util.module_from_spec(spec)

        # Inject safe dependencies
        module.__dict__['BaseTool'] = BaseTool
        module.__dict__['ToolResult'] = ToolResult
        module.__dict__['Config'] = Config

        spec.loader.exec_module(module)

        # Call create_tool factory
        if not hasattr(module, 'create_tool'):
            raise ValueError("Module missing create_tool function")

        tool = module.create_tool(self.config)

        # Load schema if present
        schema = None
        if hasattr(module, 'get_tool_schema'):
            schema = module.get_tool_schema()
            is_valid, error = ToolValidator.validate_tool_schema(schema)
            if is_valid:
                self._tool_schemas[tool.get_name()] = schema
            else:
                schema = None  # Invalid schema, don't use it

        # Register with central registry if available (single source of truth)
        if self._registry is not None:
            self._registry.register_tool(tool, schema)

        # Also store locally for get_tool_schemas() compatibility
        self._loaded_tools[tool.get_name()] = tool
        return tool

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all loaded custom tools."""
        return list(self._tool_schemas.values())

    def save_tool(self, name: str, source: str, schema: Dict[str, Any]) -> tuple[bool, str]:
        """
        Save a new custom tool to disk.

        Note: This only saves the file. Call _load_tool_from_file() after
        to load and register the tool with the central registry.

        Args:
            name: Tool name (used for filename)
            source: Python source code
            schema: Tool schema definition

        Returns:
            Tuple of (success, error_message)
        """
        try:
            self.ensure_tools_directory()

            # Validate
            is_valid, error = ToolValidator.validate_tool_code(source)
            if not is_valid:
                return False, f"Invalid tool code: {error}"

            is_valid, error = ToolValidator.validate_tool_schema(schema)
            if not is_valid:
                return False, f"Invalid tool schema: {error}"

            # Save file
            safe_name = "".join(c for c in name if c.isalnum() or c == "_").lower()
            tool_file = self.CUSTOM_TOOLS_DIR / f"{safe_name}.py"

            # Add schema as module-level function
            schema_code = f'''

def get_tool_schema():
    """Return the tool schema for API registration."""
    return {repr(schema)}
'''

            full_source = source + "\n" + schema_code
            tool_file.write_text(full_source)

            # Store the schema for this tool
            self._tool_schemas[name] = schema

            return True, ""

        except Exception as e:
            return False, str(e)


class CreateToolTool(BaseTool):
    """
    AI-facing tool for creating new custom tools.

    This tool allows the AI to extend its own capabilities by creating
    new tools that are saved to disk and loaded dynamically.
    """

    def __init__(self, config: Config, loader: DynamicToolLoader):
        """
        Initialize the tool creator.

        Args:
            config: Configuration object
            loader: DynamicToolLoader instance for saving/loading tools
        """
        super().__init__(config)
        self.loader = loader

    def get_name(self) -> str:
        """Return the tool name for registration."""
        return "create_tool"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Create a new custom tool.

        Args:
            args: Dictionary with:
                - name (str): Tool name
                - description (str): Tool description
                - source_code (str): Python source code
                - parameters (dict): JSON schema for parameters

        Returns:
            ToolResult with success/failure
        """
        try:
            name = args.get("name")
            description = args.get("description")
            source_code = args.get("source_code")
            parameters = args.get("parameters", {"type": "object", "properties": {}, "required": []})

            if not all([name, description, source_code]):
                return ToolResult.fail(
                    "Missing required arguments. Need: name, description, source_code"
                )

            # Build schema
            schema = {
                "name": name,
                "description": description,
                "parameters": parameters
            }

            # Validate and save
            success, error = self.loader.save_tool(name, source_code, schema)
            if not success:
                return ToolResult.fail(f"Failed to save tool: {error}")

            # Get the tool file path
            safe_name = "".join(c for c in name if c.isalnum() or c == "_").lower()
            tool_file = self.loader.CUSTOM_TOOLS_DIR / f"{safe_name}.py"

            # Load the new tool
            tool = self.loader._load_tool_from_file(tool_file)

            if tool:
                return ToolResult.ok(
                    f"Tool '{name}' created successfully!\n"
                    f"Location: {tool_file}\n"
                    f"The tool is now available for use.\n\n"
                    f"Note: Use /reload-tools to refresh tool definitions if needed."
                )
            else:
                return ToolResult.fail(f"Tool saved but failed to load")

        except ValueError as e:
            return ToolResult.fail(f"Validation error: {e}")
        except Exception as e:
            return ToolResult.fail(f"Error creating tool: {e}")


def create_dynamic_tools(config: Config, registry=None) -> tuple[List[BaseTool], DynamicToolLoader]:
    """
    Create dynamic tool system components.

    Args:
        config: Configuration object
        registry: Optional ToolRegistry for centralized tool registration.
                  If provided, all loaded tools will register into it,
                  maintaining a single source of truth for available capabilities.

    Returns:
        Tuple of (tools_list, loader_instance)
    """
    loader = DynamicToolLoader(config, registry=registry)
    tools = [CreateToolTool(config, loader)]

    # Load any existing custom tools
    # If registry is set, tools will be registered into it automatically
    custom_tools = loader.load_all_tools()
    tools.extend(custom_tools)

    return tools, loader
