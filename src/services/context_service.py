#!/usr/bin/env python3

"""
Context Service - Business logic for context management

Provides a facade over ContextManager with business rules and structured results.
"""

from typing import Any

from ..core.context_manager import ContextManager
from .dtos import ContextUsageSummary


class ContextService:
    """Facade for context management operations."""

    def __init__(self, context_manager: ContextManager):
        """
        Initialize ContextService.

        Args:
            context_manager: The context manager instance to wrap
        """
        self.context_manager = context_manager

    def get_usage_summary(self) -> ContextUsageSummary:
        """
        Get context usage summary.

        Returns:
            ContextUsageSummary with current usage statistics
        """
        stats = self.context_manager.get_context_stats()

        return ContextUsageSummary(
            token_count=stats["estimated_tokens"],
            percentage=stats["token_usage_percent"],
            is_warning=stats["approaching_limit"],
            is_critical=stats["critical_limit"],
            files_in_context=len(self.context_manager.mounted_files),
            max_tokens=stats["max_context_tokens"],
        )

    def get_detailed_stats(self) -> dict[str, Any]:
        """
        Get detailed context statistics.

        Returns:
            Dictionary with detailed statistics
        """
        return self.context_manager.get_context_stats()

    def get_mounted_files_count(self) -> int:
        """
        Get count of currently mounted files.

        Returns:
            Number of mounted files
        """
        return len(self.context_manager.mounted_files)

    def get_mounted_files_list(self) -> list:
        """
        Get list of mounted file paths.

        Returns:
            List of mounted file paths
        """
        return list(self.context_manager.mounted_files.keys())

    def is_at_warning_threshold(self) -> bool:
        """
        Check if context usage is at warning threshold.

        Returns:
            True if at or above warning threshold
        """
        summary = self.get_usage_summary()
        return summary.is_warning or summary.is_critical

    def is_at_critical_threshold(self) -> bool:
        """
        Check if context usage is at critical threshold.

        Returns:
            True if at or above critical threshold
        """
        summary = self.get_usage_summary()
        return summary.is_critical
