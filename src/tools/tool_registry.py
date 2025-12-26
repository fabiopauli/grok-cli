#!/usr/bin/env python3

"""
Unified Tool Registry for Grok Assistant

Solves the dual-registration problem by managing both tool schemas
(for API) and tool executors (for runtime) in one place.
"""

from typing import Any, Dict, List, Optional
from xai_sdk.chat import tool

from .base import BaseTool, ToolExecutor
from ..core.config import Config


class ToolRegistry:
    """
    Unified registry for tool schemas and executors.

    This solves the dual-registration problem where:
    - Config.get_tools() defines schemas for the API
    - ToolExecutor registers executors for runtime

    Now both are managed together, with support for dynamic registration.
    """

    def __init__(self, config: Config):
        self.config = config
        self._executor = ToolExecutor(config)
        self._dynamic_schemas: List[Dict[str, Any]] = []

    def register_tool(self, tool_instance: BaseTool, schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a tool with both executor and optional schema.

        Args:
            tool_instance: BaseTool implementation
            schema: Optional schema dict. If not provided, tool won't be exposed to API.
        """
        self._executor.register_tool(tool_instance)

        if schema:
            # Convert to xai_sdk tool format if needed
            if not isinstance(schema, dict) or 'name' not in schema:
                raise ValueError("Schema must be a dict with 'name' field")
            self._dynamic_schemas.append(schema)

    def register_tool_with_schema(
        self,
        tool_instance: BaseTool,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> None:
        """
        Register a tool with inline schema definition.

        Args:
            tool_instance: BaseTool implementation
            name: Tool name
            description: Tool description
            parameters: JSON schema for parameters
        """
        self._executor.register_tool(tool_instance)

        self._dynamic_schemas.append({
            "name": name,
            "description": description,
            "parameters": parameters
        })

    def get_all_tools(self) -> List[Any]:
        """
        Get all tool definitions for API (static + dynamic).

        Returns:
            List of tool definitions compatible with xai_sdk
        """
        # Get static tools from config
        static_tools = self.config.get_tools()

        # Add dynamic tools
        for schema in self._dynamic_schemas:
            static_tools.append(tool(
                name=schema["name"],
                description=schema["description"],
                parameters=schema["parameters"]
            ))

        return static_tools

    def get_executor(self) -> ToolExecutor:
        """Get the tool executor."""
        return self._executor

    def execute_tool_call(self, tool_call_dict: Dict[str, Any]) -> str:
        """Execute a tool call through the executor."""
        return self._executor.execute_tool_call(tool_call_dict)

    def refresh_dynamic_tools(self, loader) -> int:
        """
        Refresh dynamic tools from loader.

        Args:
            loader: DynamicToolLoader instance

        Returns:
            Number of tools refreshed
        """
        # Clear current dynamic tools
        self._dynamic_schemas.clear()

        # Reload from loader
        tools = loader.load_all_tools()
        schemas = loader.get_tool_schemas()

        for tool_inst, schema in zip(tools, schemas):
            self.register_tool(tool_inst, schema)

        return len(tools)
