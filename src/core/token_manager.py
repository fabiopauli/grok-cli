#!/usr/bin/env python3

"""
Token Manager for Grok Assistant

Handles token estimation, threshold calculation, and usage tracking.
Extracted from ContextManager for single responsibility principle.
"""

from typing import Any

from .config import Config


class TokenManager:
    """
    Manages token estimation, thresholds, and usage statistics.

    Responsibilities:
    - Calculate dynamic token thresholds based on current model
    - Estimate token usage for message lists
    - Provide usage statistics and recommendations
    - Determine when truncation is needed
    """

    def __init__(self, config: Config):
        """
        Initialize the token manager.

        Args:
            config: Configuration object with model settings
        """
        self.config = config

    def get_cache_threshold(self) -> int:
        """
        Get cache mode token threshold (90% of effective limit with buffer).

        Returns:
            Token count threshold for cache-optimized mode
        """
        buffer = getattr(self.config, 'token_buffer_percent', 0.10)
        max_tokens = self.config.get_max_tokens_for_model(self.config.current_model)
        effective_max = int(max_tokens * (1 - buffer))
        return int(effective_max * 0.9)

    def get_smart_truncation_threshold(self) -> int:
        """
        Get smart truncation threshold (70% of effective limit with buffer).

        Returns:
            Token count threshold for smart truncation mode
        """
        buffer = getattr(self.config, 'token_buffer_percent', 0.10)
        max_tokens = self.config.get_max_tokens_for_model(self.config.current_model)
        effective_max = int(max_tokens * (1 - buffer))
        return int(effective_max * 0.7)

    def estimate_context_tokens(self, messages: list[dict[str, Any]]) -> tuple[int, dict[str, int]]:
        """
        Estimate token usage for a message list.

        Args:
            messages: List of messages to estimate

        Returns:
            Tuple of (total_tokens, breakdown_by_role)
        """
        from ..utils.text_utils import estimate_token_usage
        return estimate_token_usage(messages)

    def get_usage_stats(self, messages: list[dict[str, Any]], model: str) -> dict[str, Any]:
        """
        Get comprehensive token usage statistics.

        Args:
            messages: List of messages
            model: Current model name

        Returns:
            Dictionary with usage statistics including percentages, warnings, etc.
        """
        from ..utils.text_utils import get_context_usage_info
        return get_context_usage_info(messages, model, self.config)

    def should_truncate_cache_mode(self, messages: list[dict[str, Any]]) -> bool:
        """
        Determine if truncation is needed in cache-optimized mode.

        Args:
            messages: Current message list

        Returns:
            True if truncation needed (>90% of limit)
        """
        estimated_tokens, _ = self.estimate_context_tokens(messages)
        return estimated_tokens > self.get_cache_threshold()

    def should_truncate_smart_mode(self, messages: list[dict[str, Any]]) -> bool:
        """
        Determine if truncation is needed in smart truncation mode.

        Args:
            messages: Current message list

        Returns:
            True if truncation needed (>70% of limit)
        """
        estimated_tokens, _ = self.estimate_context_tokens(messages)
        return estimated_tokens > self.get_smart_truncation_threshold()

    def get_target_tokens_after_truncation(self) -> int:
        """
        Get target token count after truncation (63% of limit).

        This ensures we stay well under the threshold after truncation
        to avoid repeated truncations.

        Returns:
            Target token count
        """
        # 90% of the 70% threshold = 63% of total limit
        return int(self.get_smart_truncation_threshold() * 0.9)
