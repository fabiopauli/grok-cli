#!/usr/bin/env python3

"""
Error handling context managers

Provides consistent error handling across the application.
"""

import json
import logging
from contextlib import contextmanager

logger = logging.getLogger("grok.errors")


@contextmanager
def handle_file_operation(operation_name: str):
    """
    Context manager for file operations with specific error handling.

    Args:
        operation_name: Name of the operation for logging

    Raises:
        FileOperationError: On file-related errors
    """
    from ..exceptions import FileOperationError

    try:
        yield
    except FileNotFoundError as e:
        logger.error(f"File not found during {operation_name}", exc_info=True)
        raise FileOperationError(f"File not found: {e}") from e
    except PermissionError as e:
        logger.error(f"Permission denied during {operation_name}", exc_info=True)
        raise FileOperationError(f"Permission denied: {e}") from e
    except OSError as e:
        logger.error(f"OS error during {operation_name}", exc_info=True)
        raise FileOperationError(f"Operation failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name}", exc_info=True)
        raise FileOperationError(f"Unexpected error: {e}") from e


@contextmanager
def handle_memory_operation(operation_name: str):
    """
    Context manager for memory operations.

    Args:
        operation_name: Name of the operation for logging

    Raises:
        MemoryOperationError: On memory-related errors
    """
    from ..exceptions import MemoryOperationError

    try:
        yield
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON during {operation_name}", exc_info=True)
        raise MemoryOperationError(f"Corrupted memory data: {e}") from e
    except KeyError as e:
        logger.error(f"Missing key during {operation_name}", exc_info=True)
        raise MemoryOperationError(f"Invalid memory structure: missing {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name}", exc_info=True)
        raise MemoryOperationError(f"Memory operation failed: {e}") from e


@contextmanager
def handle_context_operation(operation_name: str):
    """
    Context manager for context operations.

    Args:
        operation_name: Name of the operation for logging

    Raises:
        ContextError: On context-related errors
    """
    from ..exceptions import ContextError

    try:
        yield
    except Exception as e:
        logger.error(f"Error during {operation_name}", exc_info=True)
        raise ContextError(f"Context operation failed: {e}") from e


@contextmanager
def handle_tool_execution(tool_name: str):
    """
    Context manager for tool execution.

    Args:
        tool_name: Name of the tool being executed

    Raises:
        ToolExecutionError: On tool execution errors
    """
    from ..exceptions import ToolExecutionError

    try:
        yield
    except KeyError as e:
        logger.error(f"Missing argument in {tool_name}", exc_info=True)
        raise ToolExecutionError(f"Missing required argument: {e}") from e
    except Exception as e:
        logger.error(f"Error executing {tool_name}", exc_info=True)
        raise ToolExecutionError(f"Tool execution failed: {e}") from e
