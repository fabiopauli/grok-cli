#!/usr/bin/env python3

"""
Context Manager for Grok Assistant

Coordinates context management using focused components.
Refactored from God Object to thin orchestrator pattern (Phase 2).
"""

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.text_utils import estimate_tokens_from_text
from .config import Config
from .context_builder import ContextBuilder, ContextMode
from .token_manager import TokenManager
from .truncation_strategy import TruncationStrategy
from .turn_logger import Turn, TurnLogger


@dataclass
class FileContext:
    """
    Represents a file mounted in the context.
    These files persist across truncations and are injected fresh on every API call.
    """

    path: str  # Normalized absolute path
    content: str  # The file content
    token_count: int  # Cached token usage
    timestamp: float  # Last update time


class ContextManager:
    """
    Coordinates context management using focused components.

    Phase 2 refactoring: Now a thin orchestrator instead of God Object.
    Delegates to TokenManager, TruncationStrategy, and ContextBuilder.
    """

    def __init__(self, config: Config):
        """
        Initialize the context manager with component-based architecture.

        Args:
            config: Configuration object
        """
        self.config = config
        # Set initial mode from config
        if hasattr(config, 'initial_context_mode'):
            if config.initial_context_mode == "cache_optimized":
                self.mode = ContextMode.CACHE_OPTIMIZED
            else:
                self.mode = ContextMode.SMART_TRUNCATION  # Default
        else:
            self.mode = ContextMode.SMART_TRUNCATION  # Fallback default

        # Phase 2: Focused components (single responsibility)
        self.token_manager = TokenManager(config)
        self.truncation_strategy = TruncationStrategy(config)
        self.context_builder = ContextBuilder(config)
        self.turn_logger = TurnLogger(config)

        # Context storage (simplified)
        self._system_messages: list[dict[str, Any]] = []  # System messages only
        self.turn_logs: list[Turn] = []  # Summarized turn logs
        self.memories: list[dict[str, Any]] = []  # Persistent memories
        self.task_summary: str = ""  # Current task summary

        # Phase 3: Layered Context Model - Mounted Resources
        # Files mounted here persist across truncations
        self.mounted_files: dict[str, FileContext] = {}  # path -> FileContext

        # Phase 2 Token Optimization: Deduplication tracking
        self._files_in_context: set[str] = set()  # Normalized paths of files already in context
        self._system_message_hashes: set[str] = set()  # Track system message content hashes

    @property
    def full_context(self) -> list[dict[str, Any]]:
        """
        Derive full context from turn logs (single source of truth).
        System messages + completed turns + current active turn.
        """
        messages = self._system_messages.copy()

        # Add messages from completed turns
        if self.turn_logs:
            completed_messages = self.turn_logger.get_all_messages_from_turns(self.turn_logs)
            messages.extend(completed_messages)

        # Add messages from current active turn
        if self.turn_logger.is_turn_active():
            messages.extend(self.turn_logger.get_turn_events_as_messages())

        # Defensive: Filter out non-dict items and log warnings
        valid_messages = []
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                print(f"WARNING: Non-dict message at index {i}: {type(msg)} = {repr(msg)[:100]}")
                continue
            valid_messages.append(msg)

        return valid_messages

    @property
    def cache_token_threshold(self) -> int:
        """
        Dynamic threshold that updates when model changes (90% of current model's limit).
        Phase 2: Delegates to TokenManager.
        """
        return self.token_manager.get_cache_threshold()

    @property
    def smart_truncation_threshold(self) -> int:
        """
        Dynamic threshold that updates when model changes (70% of current model's limit).
        Phase 2: Delegates to TokenManager.
        """
        return self.token_manager.get_smart_truncation_threshold()

    def set_mode(self, mode: ContextMode) -> None:
        """
        Set the context management mode.

        Args:
            mode: Context management mode to use
        """
        old_mode = self.mode
        self.mode = mode

        # If switching from cache to smart mode, apply immediate truncation
        if old_mode == ContextMode.CACHE_OPTIMIZED and mode == ContextMode.SMART_TRUNCATION:
            self._apply_smart_truncation()

    def get_mode(self) -> ContextMode:
        """Get the current context management mode."""
        return self.mode

    def set_memories(self, memories: list[dict[str, Any]]) -> None:
        """
        Set the persistent memories for context injection.

        Args:
            memories: List of memory objects to inject into context
        """
        self.memories = memories

    def set_task_summary(self, task_summary: str) -> None:
        """
        Set the current task summary for context injection.

        Args:
            task_summary: Task summary string from TaskManager
        """
        self.task_summary = task_summary

    def mount_file(self, path: str, content: str) -> None:
        """
        Mount a file into the context. Mounted files persist across truncations
        and are injected fresh on every API call.

        Args:
            path: File path to mount
            content: File content
        """
        # Normalize the path to absolute form
        normalized_path = str(Path(path).resolve())

        # Estimate token usage for the content
        token_count = estimate_tokens_from_text(content)

        # Create FileContext and add to mounted files
        file_context = FileContext(
            path=normalized_path, content=content, token_count=token_count, timestamp=time.time()
        )

        self.mounted_files[normalized_path] = file_context
        self.add_file_to_context(normalized_path)

    def unmount_file(self, path: str) -> bool:
        """
        Remove a file from the mounted context.

        Args:
            path: File path to unmount

        Returns:
            True if file was mounted and removed, False otherwise
        """
        # Normalize the path to absolute form
        normalized_path = str(Path(path).resolve())

        # Remove from mounted files if present
        if normalized_path in self.mounted_files:
            del self.mounted_files[normalized_path]
            return True

        return False

    def get_mounted_files(self) -> dict[str, FileContext]:
        """
        Get all currently mounted files.

        Returns:
            Dictionary of path -> FileContext for all mounted files
        """
        return self.mounted_files.copy()

    def refresh_mounted_file_if_exists(self, path: str) -> bool:
        """
        Refresh a mounted file's content from disk if it exists.
        This prevents the "stale mount" problem where files are modified
        on disk but the cached content in memory becomes outdated.

        Args:
            path: File path to refresh

        Returns:
            True if file was mounted and refreshed, False otherwise
        """
        normalized_path = str(Path(path).resolve())

        if normalized_path in self.mounted_files:
            # Re-read from disk
            try:
                with open(normalized_path, 'r', encoding='utf-8') as f:
                    new_content = f.read()

                # Update mounted file with fresh content
                token_count = estimate_tokens_from_text(new_content)
                self.mounted_files[normalized_path] = FileContext(
                    path=normalized_path,
                    content=new_content,
                    token_count=token_count,
                    timestamp=time.time()
                )
                return True
            except Exception as e:
                # If we can't read the file, it might have been deleted
                # In that case, unmount it
                print(f"Warning: Failed to refresh mounted file {path}: {e}")
                print(f"  Unmounting file from context.")
                del self.mounted_files[normalized_path]
                return False

        return False

    def add_file_to_context(self, path: str) -> None:
        """
        Track that a file's content is now in context.

        Args:
            path: File path to track
        """
        # Check if deduplication is enabled
        if hasattr(self.config, 'deduplicate_file_content') and self.config.deduplicate_file_content:
            normalized_path = str(Path(path).resolve())
            self._files_in_context.add(normalized_path)

    def is_file_in_context(self, path: str) -> bool:
        """
        Check if file content is already in context (mounted or recently read).

        Args:
            path: File path to check

        Returns:
            True if file is already in context, False otherwise
        """
        # Check if deduplication is enabled
        if not hasattr(self.config, 'deduplicate_file_content') or not self.config.deduplicate_file_content:
            return False

        normalized_path = str(Path(path).resolve())
        return normalized_path in self._files_in_context or normalized_path in self.mounted_files

    def clear_file_tracking(self) -> None:
        """Clear file tracking (called on context clear)."""
        self._files_in_context.clear()

    def add_system_message(self, content: str) -> bool:
        """
        Add a system message to the context.

        Args:
            content: System message content

        Returns:
            True if message was added, False if duplicate
        """
        # Check for duplicates using content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self._system_message_hashes:
            return False  # Duplicate, skip

        self._system_message_hashes.add(content_hash)
        message = {"role": "system", "content": content}
        self._system_messages.append(message)
        return True

    def start_turn(self, user_message: str) -> str:
        """
        Start a new conversation turn.

        Args:
            user_message: User message that starts the turn

        Returns:
            Turn ID for the new turn
        """
        # Check if we should truncate before starting new turn
        if self.mode == ContextMode.CACHE_OPTIMIZED:
            self._check_cache_truncation()

        # Start turn logging (turn becomes part of full_context automatically via property)
        turn_id = self.turn_logger.start_turn(user_message)

        return turn_id

    def add_assistant_message(
        self, content: str, tool_calls: list[dict[str, Any]] | None = None
    ) -> None:
        """
        Add an assistant message to the current turn.

        Args:
            content: Assistant message content
            tool_calls: Optional tool calls made by the assistant
        """
        # Log to turn logger (becomes part of full_context automatically via property)
        self.turn_logger.add_assistant_message(content)

    def add_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """
        Add a tool call to the current turn.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
        """
        self.turn_logger.add_tool_call(tool_name, args)

    def add_tool_response(self, tool_name: str, result: str) -> None:
        """
        Add a tool response to the current turn.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
        """
        # Log to turn logger (becomes part of full_context automatically via property)
        self.turn_logger.add_tool_response(tool_name, result)

    def complete_turn(self, summary: str | None = None) -> Turn | None:
        """
        Complete the current turn and apply truncation if needed.

        Args:
            summary: Optional summary of what was accomplished

        Returns:
            The completed turn if one was active
        """
        if not self.turn_logger.is_turn_active():
            return None

        # Complete the turn
        completed_turn = self.turn_logger.complete_turn(summary)

        # Apply mode-specific context management
        if self.mode == ContextMode.SMART_TRUNCATION:
            # Immediately convert turn to log and truncate
            self.turn_logs.append(completed_turn)
            self._apply_smart_truncation()
        else:
            # Cache mode: just store the turn log for potential future truncation
            self.turn_logs.append(completed_turn)

        return completed_turn

    def get_context_for_api(self) -> list[dict[str, Any]]:
        """
        Get the current context formatted for API calls.

        Phase 3: Implements Layered Context Model:
        - Layer 1: System & Identity (Fixed)
        - Layer 2: Mounted Resources (Persistent, immune to truncation)
        - Layer 3: Dialogue Stream (Ephemeral, subject to truncation)

        Returns:
            List of messages ready for API consumption
        """
        # LAYER 1: Build base context with system prompt and memories
        base_context = self.context_builder.build_full_api_context(
            system_messages=self._system_messages,
            turn_logs=[],  # We'll add dialogue layer separately
            current_turn_messages=[],
            memories=self.memories,
            mode=self.mode,
            task_summary=self.task_summary,
        )

        # LAYER 2: Inject mounted files as system messages (persistent layer)
        mounted_files_messages = self._build_mounted_files_context()

        # LAYER 3: Get dialogue stream (current turn + turn logs)
        current_turn_messages = []
        if self.turn_logger.is_turn_active():
            current_turn_messages = self.turn_logger.get_turn_events_as_messages()
        elif self.mode == ContextMode.CACHE_OPTIMIZED:
            # In cache mode, include all non-system messages from full_context
            current_turn_messages = [
                msg
                for msg in self.full_context
                if isinstance(msg, dict) and msg.get("role") != "system"
            ]

        dialogue_context = self.context_builder.build_full_api_context(
            system_messages=[],  # No system messages in dialogue layer
            turn_logs=self.turn_logs,
            current_turn_messages=current_turn_messages,
            memories=[],  # No memories in dialogue layer
            mode=self.mode,
        )

        # Calculate token usage for each layer
        layer1_tokens, _ = self.token_manager.estimate_context_tokens(base_context)
        layer2_tokens, _ = self.token_manager.estimate_context_tokens(mounted_files_messages)
        layer3_tokens, _ = self.token_manager.estimate_context_tokens(dialogue_context)

        total_tokens = layer1_tokens + layer2_tokens + layer3_tokens
        max_tokens = self.config.get_max_tokens_for_model(self.config.current_model)

        # If we're over budget, aggressively truncate Layer 3 to preserve Layers 1 & 2
        if total_tokens > max_tokens:
            # Calculate how many tokens we can allocate to dialogue
            available_for_dialogue = max_tokens - layer1_tokens - layer2_tokens

            if available_for_dialogue < self.config.min_dialogue_tokens:
                # Emergency: Not enough space for meaningful dialogue
                # Keep only the current turn if active
                if self.turn_logger.is_turn_active():
                    dialogue_context = self.turn_logger.get_turn_events_as_messages()
                else:
                    dialogue_context = []
            else:
                # Truncate dialogue to fit available space
                truncated_logs = self.truncation_strategy.truncate_turns(
                    self.turn_logs,
                    available_for_dialogue,
                    self.token_manager.estimate_context_tokens,
                )
                dialogue_context = self.context_builder.build_full_api_context(
                    system_messages=[],
                    turn_logs=truncated_logs,
                    current_turn_messages=current_turn_messages,
                    memories=[],
                    mode=self.mode,
                )

        # Assemble final context: Layer 1 + Layer 2 + Layer 3
        final_context = base_context + mounted_files_messages + dialogue_context

        return final_context

    def _build_mounted_files_context(self) -> list[dict[str, Any]]:
        """
        Build context messages for mounted files (Layer 2).
        These are injected as system messages and persist across truncations.

        Returns:
            List of system messages containing mounted file contents
        """
        if not self.mounted_files:
            return []

        messages = []

        # Sort files by path for consistent ordering
        sorted_files = sorted(self.mounted_files.items(), key=lambda x: x[0])

        for path, file_context in sorted_files:
            # Use relative path if enabled
            if self.config.use_relative_paths:
                try:
                    rel_path = Path(path).relative_to(self.config.base_dir)
                except ValueError:
                    rel_path = Path(path).name  # Fallback to filename
            else:
                rel_path = path

            # Compact format: [filename] content (no metadata)
            message_content = f"[{rel_path}]\n{file_context.content}"

            messages.append({"role": "system", "content": message_content})

        return messages

    def _build_system_prompt(self) -> str:
        """
        Build system prompt with memories included.
        Phase 2: Delegates to ContextBuilder.
        """
        return self.context_builder.build_system_prompt(self.memories)

    def _build_context_from_turn_logs(self) -> list[dict[str, Any]]:
        """
        Build context messages from turn logs.
        Phase 2: Delegates to ContextBuilder.
        """
        return self.context_builder.build_context_from_turns(self.turn_logs, self.mode)

    def _turn_to_messages(self, turn: Turn) -> list[dict[str, Any]]:
        """
        Convert a turn log back to message format.
        Phase 2: Delegates to ContextBuilder.
        """
        return self.context_builder.turn_to_messages(turn)

    def _get_recent_full_context(self) -> list[dict[str, Any]]:
        """Get recent full context messages."""
        if self.mode == ContextMode.SMART_TRUNCATION:
            # Return messages from current turn only
            if self.turn_logger.is_turn_active():
                return self.turn_logger.get_turn_events_as_messages()
            else:
                return []
        else:
            # Cache mode: return full context excluding system messages
            # (system prompt is already added in get_context_for_api)
            return [
                msg
                for msg in self.full_context
                if isinstance(msg, dict) and msg.get("role") != "system"
            ]

    def _check_cache_truncation(self) -> None:
        """
        Check if cache mode needs truncation and apply if necessary.
        Phase 2: Uses TokenManager to check threshold.
        """
        if self.mode != ContextMode.CACHE_OPTIMIZED:
            return

        # Use TokenManager to check if truncation needed
        if self.token_manager.should_truncate_cache_mode(self.full_context):
            self._apply_cache_truncation()

    def _apply_cache_truncation(self) -> None:
        """
        Apply truncation for cache-optimized mode.
        Phase 2: Delegates to TruncationStrategy.
        """
        # Convert context to turn logs and apply smart truncation
        self._convert_full_context_to_turns()
        self._apply_smart_truncation()
        # Note: full_context is now a derived property, no need to clear it

    def _apply_smart_truncation(self) -> None:
        """
        Apply smart truncation keeping only essential turn logs.
        Phase 2: Delegates to TruncationStrategy.
        """
        # Get target token count from TokenManager
        target_tokens = self.token_manager.get_target_tokens_after_truncation()

        # Get current context and estimate tokens
        current_context = self.get_context_for_api()
        estimated_tokens, _ = self.token_manager.estimate_context_tokens(current_context)

        # Only truncate if we're over the target
        if estimated_tokens <= target_tokens:
            return

        # Delegate truncation to TruncationStrategy
        self.turn_logs = self.truncation_strategy.truncate_turns(
            self.turn_logs, target_tokens, self.token_manager.estimate_context_tokens
        )

    def _convert_full_context_to_turns(self) -> None:
        """
        Convert full context to turn logs.
        Phase 2: Delegates to TruncationStrategy.
        """
        if not self.full_context:
            return

        # Delegate to TruncationStrategy
        turn_counter = len(self.turn_logs) + 1
        new_turns = self.truncation_strategy.convert_messages_to_turns(
            self.full_context, turn_counter
        )

        # Append new turns to existing turn logs
        self.turn_logs.extend(new_turns)

    def get_context_stats(self) -> dict[str, Any]:
        """
        Get context usage statistics.
        Phase 3: Includes mounted files information.

        Returns:
            Dictionary with context usage information
        """
        current_context = self.get_context_for_api()

        # Delegate to TokenManager for usage info
        context_info = self.token_manager.get_usage_stats(
            current_context, self.config.current_model
        )

        # Calculate mounted files token usage
        mounted_files_tokens = sum(fc.token_count for fc in self.mounted_files.values())

        stats = {
            **context_info,
            "mode": self.mode.value,
            "turn_logs_count": len(self.turn_logs),
            "full_context_messages": len(self.full_context),
            "memories_count": len(self.memories),
            "mounted_files_count": len(self.mounted_files),
            "mounted_files_tokens": mounted_files_tokens,
            "active_turn": self.turn_logger.is_turn_active(),
        }

        return stats

    def clear_context(self, keep_memories: bool = True, keep_mounted_files: bool = False) -> None:
        """
        Clear all context data.

        Args:
            keep_memories: Whether to keep persistent memories
            keep_mounted_files: Whether to keep mounted files (default: False)
        """
        self._system_messages = []
        self._system_message_hashes.clear()
        self.turn_logs = []

        if not keep_memories:
            self.memories = []

        if not keep_mounted_files:
            self.mounted_files = {}
            self.clear_file_tracking()

        # Reset turn logger
        if self.turn_logger.is_turn_active():
            self.turn_logger.complete_turn("Context cleared")

    def export_context(self, include_full_context: bool = False) -> dict[str, Any]:
        """
        Export context data for debugging or analysis.

        Args:
            include_full_context: Whether to include full message history

        Returns:
            Dictionary containing context data
        """
        export_data = {
            "mode": self.mode.value,
            "memories": self.memories,
            "turn_logs": [turn.to_dict() for turn in self.turn_logs],
            "mounted_files": {
                path: {
                    "path": fc.path,
                    "token_count": fc.token_count,
                    "timestamp": fc.timestamp,
                    "content_preview": fc.content[:200] + "..."
                    if len(fc.content) > 200
                    else fc.content,
                }
                for path, fc in self.mounted_files.items()
            },
            "stats": self.get_context_stats(),
        }

        if include_full_context:
            export_data["full_context"] = self.full_context

        return export_data
