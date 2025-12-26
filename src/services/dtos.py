#!/usr/bin/env python3

"""
Data Transfer Objects (DTOs) for service layer

These dataclasses provide structured, typed results from service operations,
decoupling business logic from UI presentation.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReadResult:
    """Result of a file read operation."""

    success: bool
    content: str | None
    error: str | None
    path: str


@dataclass
class MountResult:
    """Result of mounting files to context."""

    mounted: bool
    path: str
    files_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class MemoryListResult:
    """Result of listing memories."""

    memories: list[dict[str, Any]]
    total_count: int
    scope: str  # "global", "directory", "all"


@dataclass
class MemorySaveResult:
    """Result of saving a memory."""

    success: bool
    memory_id: str | None
    error: str | None = None


@dataclass
class MemoryRemoveResult:
    """Result of removing a memory."""

    success: bool
    memory_id: str
    found: bool


@dataclass
class MemoryClearResult:
    """Result of clearing memories."""

    cleared_count: int
    scope: str  # "global", "directory", "all"


@dataclass
class ContextUsageSummary:
    """Summary of context usage."""

    token_count: int
    percentage: float
    is_warning: bool
    is_critical: bool
    files_in_context: int
    max_tokens: int


@dataclass
class FileResolveResult:
    """Result of resolving a file path."""

    success: bool
    resolved_path: str | None
    original_path: str
    error: str | None = None
    was_fuzzy_match: bool = False
