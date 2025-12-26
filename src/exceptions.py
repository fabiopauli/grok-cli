#!/usr/bin/env python3

"""
Custom exceptions for Grok Assistant

Provides specific exception types for better error handling and debugging.
"""


class GrokError(Exception):
    """Base exception for all Grok errors."""

    pass


class FileOperationError(GrokError):
    """File operations failed."""

    pass


class MemoryOperationError(GrokError):
    """Memory operations failed."""

    pass


class ValidationError(GrokError):
    """Data validation failed."""

    pass


class ContextError(GrokError):
    """Context management error."""

    pass


class ToolExecutionError(GrokError):
    """Tool execution failed."""

    pass


class ConfigurationError(GrokError):
    """Configuration error."""

    pass
