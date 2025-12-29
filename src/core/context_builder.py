#!/usr/bin/env python3

"""
Context Builder for Grok Assistant

Builds API-ready context from turns and memories.
Extracted from ContextManager for cleaner separation of concerns.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
import hashlib
from .config import Config
from .turn_logger import Turn


@dataclass
class CacheMetadata:
    """Metadata for prompt caching."""
    system_prompt_hash: str
    mounted_files_hash: str
    cache_breakpoint_index: int  # Where stable prefix ends


class ContextMode(Enum):
    """Context management modes."""
    CACHE_OPTIMIZED = "cache_optimized"  # Append-only until truncation
    SMART_TRUNCATION = "smart_truncation"  # Immediate turn summarization


class ContextBuilder:
    """
    Builds API-ready context from turns and memories.

    Responsibilities:
    - Build system prompts with memory injection
    - Convert turn logs to API message format
    - Handle different context modes (cache vs smart truncation)
    """

    def __init__(self, config: Config):
        """
        Initialize the context builder.

        Args:
            config: Configuration object
        """
        self.config = config
        self._cache_metadata: Optional[CacheMetadata] = None

    def _compute_hash(self, content: str) -> str:
        """Compute hash for cache validation."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_cache_metadata(self) -> Optional[CacheMetadata]:
        """Get current cache metadata for monitoring."""
        return self._cache_metadata

    def is_cache_valid(self, new_prompt: str, new_files: str) -> bool:
        """Check if cache would still be valid with new content."""
        if not self._cache_metadata:
            return False
        return (
            self._compute_hash(new_prompt) == self._cache_metadata.system_prompt_hash and
            self._compute_hash(new_files) == self._cache_metadata.mounted_files_hash
        )

    def build_system_prompt(self, memories: List[Dict[str, Any]], task_summary: str = "") -> str:
        """
        Build system prompt with memories and task summary included.

        Args:
            memories: List of memory objects to inject
            task_summary: Optional task summary to inject

        Returns:
            Formatted system prompt string with memories and tasks
        """
        # Get base system prompt
        base_prompt = self.config.get_system_prompt()

        sections = []

        # Add task summary if present (shown first for visibility)
        if task_summary:
            sections.append(f"\n\n## Current Tasks\n\n{task_summary}")

        # Add memories if any exist
        if memories:
            if self.config.compact_memory_format:
                # Compact format: [type] content
                memory_section = "\n\nMemories:\n"
                for memory in memories:
                    memory_type = memory.get("type", "note")
                    content = memory.get("content", "")
                    memory_section += f"[{memory_type}] {content}\n"
            else:
                # Original verbose format
                memory_section = "\n\n## Persistent Memories\n\n"
                for memory in memories:
                    memory_type = memory.get("type", "note")
                    content = memory.get("content", "")
                    memory_section += f"- **{memory_type.replace('_', ' ').title()}**: {content}\n"
            sections.append(memory_section)

        return base_prompt + "".join(sections)

    def build_context_from_turns(
        self,
        turn_logs: List[Turn],
        mode: ContextMode
    ) -> List[Dict[str, Any]]:
        """
        Build context messages from turn logs.

        Args:
            turn_logs: Completed turns
            mode: Context mode (affects how turns are formatted)

        Returns:
            List of context messages in API format
        """
        context = []

        if not turn_logs:
            return context

        # Add turn summaries as system messages for older turns
        # Keep last 3 turns in full detail
        for turn_log in turn_logs[:-3]:
            summary_msg = {
                "role": "system",
                "content": f"Previous turn summary: {turn_log.summary}"
            }
            context.append(summary_msg)

        # Add last few turns in full detail
        for turn_log in turn_logs[-3:]:
            context.extend(self.turn_to_messages(turn_log))

        return context

    def turn_to_messages(self, turn: Turn) -> List[Dict[str, Any]]:
        """
        Convert a turn to message format.

        Args:
            turn: Turn to convert

        Returns:
            List of messages in API format
        """
        messages = []

        for event in turn.events:
            if event.type == "user_message":
                messages.append({"role": "user", "content": event.content})
            elif event.type == "assistant_message":
                messages.append({"role": "assistant", "content": event.content})
            elif event.type == "tool_response":
                messages.append({"role": "tool", "content": event.result})

        return messages

    def build_full_api_context(
        self,
        system_messages: List[Dict[str, Any]],
        turn_logs: List[Turn],
        current_turn_messages: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
        mode: ContextMode,
        task_summary: str = "",
        enable_cache_hints: bool = False,
        include_system_prompt: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Build complete API-ready context with optional cache hints.

        Args:
            system_messages: System messages
            turn_logs: Completed turn logs
            current_turn_messages: Messages from active turn
            memories: Persistent memories
            mode: Context mode
            task_summary: Optional task summary to inject
            enable_cache_hints: Whether to add cache control metadata (default: False)
            include_system_prompt: Whether to include the system prompt (default: True)

        Returns:
            Complete list of messages ready for API
        """
        context = []

        # Add system prompt (always first) - STABLE PREFIX LAYER 1
        # Only add if requested (to avoid duplicates)
        if include_system_prompt:
            system_prompt = self.build_system_prompt(memories, task_summary)
            system_msg = {"role": "system", "content": system_prompt}

            if enable_cache_hints:
                system_msg["cache_control"] = {"type": "ephemeral"}  # xAI API format TBD

            context.append(system_msg)

        # Add other system messages (mounted files) - STABLE PREFIX LAYER 2
        cache_breakpoint = len(context)
        for msg in system_messages:
            context.append(msg)
            if enable_cache_hints and "User added file" in msg.get("content", ""):
                # Mark mounted files as cacheable
                context[-1]["cache_control"] = {"type": "ephemeral"}

        cache_breakpoint = len(context)

        # Add context based on mode - DIALOGUE STREAM (not cached)
        if mode == ContextMode.SMART_TRUNCATION and turn_logs:
            # Use turn logs for older context
            context.extend(self.build_context_from_turns(turn_logs, mode))
        elif mode == ContextMode.CACHE_OPTIMIZED and turn_logs:
            # In cache mode, include all turn messages in full
            for turn_log in turn_logs:
                context.extend(self.turn_to_messages(turn_log))

        # Add current turn messages
        context.extend(current_turn_messages)

        # Update cache metadata
        if enable_cache_hints:
            system_hash = self._compute_hash(system_prompt)
            files_hash = self._compute_hash(str(system_messages))
            self._cache_metadata = CacheMetadata(
                system_prompt_hash=system_hash,
                mounted_files_hash=files_hash,
                cache_breakpoint_index=cache_breakpoint
            )

        return context
