#!/usr/bin/env python3

"""
Service layer for Grok Assistant

This module contains pure business logic extracted from commands,
enabling better testing and separation of concerns.
"""

from .context_service import ContextService
from .dtos import (
    ContextUsageSummary,
    FileResolveResult,
    MemoryClearResult,
    MemoryListResult,
    MemoryRemoveResult,
    MemorySaveResult,
    MountResult,
    ReadResult,
)
from .file_service import FileService
from .memory_service import MemoryService

__all__ = [
    # DTOs
    "ReadResult",
    "MountResult",
    "MemoryListResult",
    "MemorySaveResult",
    "MemoryRemoveResult",
    "MemoryClearResult",
    "ContextUsageSummary",
    "FileResolveResult",
    # Services
    "MemoryService",
    "FileService",
    "ContextService",
]
