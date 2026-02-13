#!/usr/bin/env python3

"""
Base tool handler for Grok Assistant

Provides the foundation for implementing tool handlers.
"""

import json
from abc import ABC, abstractmethod
from typing import Any

from ..core.config import Config


class ToolResult:
    """Result of a tool execution."""

    def __init__(self, success: bool, result: str, error: str | None = None):
        self.success = success
        self.result = result
        self.error = error

    @classmethod
    def ok(cls, result: str) -> 'ToolResult':
        """Create a successful result."""
        return cls(success=True, result=result)

    @classmethod
    def fail(cls, error: str) -> 'ToolResult':
        """Create an error result."""
        return cls(success=False, result=error, error=error)


class BaseTool(ABC):
    """Base class for all tool handlers."""

    def __init__(self, config: Config):
        """Initialize the tool handler."""
        self.config = config
        self.context_manager = None  # Optional context manager for mounted file tracking

    @abstractmethod
    def get_name(self) -> str:
        """Get the tool name."""
        pass

    @abstractmethod
    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute the tool with given arguments."""
        pass

    def get_schema(self) -> dict[str, Any] | None:
        """
        Return the JSON schema definition for this tool.

        Override in subclasses to co-locate schema with implementation.
        Returns None if this tool's schema is defined elsewhere (legacy).
        Schema format: {"name": str, "description": str, "parameters": dict}
        """
        return None

    def set_context_manager(self, context_manager) -> None:
        """
        Set the context manager for this tool.
        Used by file tools to refresh mounted files after modifications.

        Args:
            context_manager: ContextManager instance
        """
        self.context_manager = context_manager

    def success(self, message: str) -> ToolResult:
        """
        Helper method to create a successful ToolResult.

        Args:
            message: Success message

        Returns:
            ToolResult indicating success
        """
        return ToolResult.ok(message)

    def error(self, message: str) -> ToolResult:
        """
        Helper method to create an error ToolResult.

        Args:
            message: Error message

        Returns:
            ToolResult indicating failure
        """
        return ToolResult.fail(message)


class ToolExecutor:
    """Tool execution coordinator."""

    def __init__(self, config: Config):
        """Initialize the tool executor."""
        self.config = config
        self.tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool handler."""
        self.tools[tool.get_name()] = tool

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """
        Collect tool schemas from all registered tools that define get_schema().

        Returns:
            List of tool schema dicts for tools that co-locate their schemas.
        """
        schemas = []
        for tool in self.tools.values():
            schema = tool.get_schema()
            if schema is not None:
                schemas.append(schema)
        return schemas

    def inject_context_manager(self, context_manager) -> None:
        """
        Inject context manager into all registered tools.
        This is used to fix the stale mount problem by allowing file tools
        to refresh mounted files after modifications.

        Args:
            context_manager: ContextManager instance to inject
        """
        for tool in self.tools.values():
            if hasattr(tool, 'set_context_manager'):
                tool.set_context_manager(context_manager)

    def execute_tool_call(self, tool_call_dict: dict[str, Any]) -> ToolResult:
        """
        Execute a function call from the LLM.

        Args:
            tool_call_dict: Dictionary containing function call information

        Returns:
            ToolResult with structured success/failure information

        Raises:
            TaskCompletionSignal: When task_completed tool is called (let it propagate)
        """
        from .lifecycle_tools import TaskCompletionSignal

        func_name = "unknown_function"
        try:
            func_name = tool_call_dict["function"]["name"]
            args = json.loads(tool_call_dict["function"]["arguments"])

            # Find and execute the appropriate tool
            if func_name in self.tools:
                tool = self.tools[func_name]
                return tool.execute(args)
            else:
                return ToolResult.fail(
                    f"Error: Unknown function '{func_name}'. Available functions: {list(self.tools.keys())}"
                )

        except TaskCompletionSignal:
            raise
        except json.JSONDecodeError as e:
            return ToolResult.fail(f"Error: Invalid JSON in function arguments for '{func_name}': {str(e)}")
        except Exception as e:
            return ToolResult.fail(f"Error executing function '{func_name}': {str(e)}")
