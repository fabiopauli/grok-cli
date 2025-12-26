#!/usr/bin/env python3

"""
Base tool handler for Grok Assistant

Provides the foundation for implementing tool handlers.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..core.config import Config


class ToolResult:
    """Result of a tool execution."""
    
    def __init__(self, success: bool, result: str, error: Optional[str] = None):
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

    # Backward compatibility aliases (deprecated)
    success = ok
    error = fail


class BaseTool(ABC):
    """Base class for all tool handlers."""
    
    def __init__(self, config: Config):
        """Initialize the tool handler."""
        self.config = config
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the tool name."""
        pass
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """Execute the tool with given arguments."""
        pass


class ToolExecutor:
    """Tool execution coordinator."""
    
    def __init__(self, config: Config):
        """Initialize the tool executor."""
        self.config = config
        self.tools: Dict[str, BaseTool] = {}
    
    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool handler."""
        self.tools[tool.get_name()] = tool
    
    def execute_tool_call(self, tool_call_dict: Dict[str, Any]) -> str:
        """
        Execute a function call from the LLM.

        Args:
            tool_call_dict: Dictionary containing function call information

        Returns:
            String result of the function execution

        Raises:
            TaskCompletionSignal: When task_completed tool is called (let it propagate)
        """
        func_name = "unknown_function"
        try:
            func_name = tool_call_dict["function"]["name"]
            args = json.loads(tool_call_dict["function"]["arguments"])

            # Find and execute the appropriate tool
            if func_name in self.tools:
                tool = self.tools[func_name]
                result = tool.execute(args)
                return result.result
            else:
                return f"Error: Unknown function '{func_name}'. Available functions: {list(self.tools.keys())}"

        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON in function arguments for '{func_name}': {str(e)}"
        except Exception as e:
            # Let TaskCompletionSignal propagate (don't catch it)
            # Import here to avoid circular dependency
            from .lifecycle_tools import TaskCompletionSignal
            if isinstance(e, TaskCompletionSignal):
                raise
            return f"Error executing function '{func_name}': {str(e)}"