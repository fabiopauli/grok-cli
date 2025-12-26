#!/usr/bin/env python3

"""
Truncation Strategy for Grok Assistant

Handles context truncation logic with turn-aware compression.
Extracted from ContextManager for testability and flexibility.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from .config import Config
from .turn_logger import Turn, TurnEvent


class TruncationStrategy:
    """
    Handles context truncation with turn-aware compression.

    Responsibilities:
    - Truncate turn logs to stay under token limits
    - Compress multiple turns into summary turns
    - Preserve recent context while summarizing older turns
    """

    def __init__(self, config: Config):
        """
        Initialize the truncation strategy.

        Args:
            config: Configuration object
        """
        self.config = config
        # Make sliding window size configurable
        self.min_preserved_turns = getattr(config, 'min_preserved_turns', 3)

    def truncate_turns(
        self,
        turn_logs: list[Turn],
        target_tokens: int,
        token_estimator: Callable[[list[dict[str, Any]]], tuple[int, dict[str, int]]],
    ) -> list[Turn]:
        """
        Apply sliding window truncation to turn logs.

        Strategy: Preserve last N turns in full detail (sliding window),
        compress all older turns into a single summary turn.

        Args:
            turn_logs: List of turns to truncate
            target_tokens: Target token count after truncation
            token_estimator: Function to estimate tokens from messages

        Returns:
            Truncated list of turns
        """
        if not turn_logs:
            return []

        # Step 1: Check if truncation is needed
        current_messages = []
        for turn in turn_logs:
            current_messages.extend(self._turn_to_messages(turn))

        current_tokens, _ = token_estimator(current_messages)

        if current_tokens <= target_tokens:
            # Under budget - no truncation needed
            return turn_logs

        # Step 2: Calculate sliding window split point
        if len(turn_logs) <= self.min_preserved_turns:
            # We have few turns but are over limit - keep only last turn + compress rest
            split_index = max(0, len(turn_logs) - 1)
        else:
            # Standard sliding window: compress older, preserve recent
            split_index = len(turn_logs) - self.min_preserved_turns

        # Ensure valid split
        split_index = max(0, split_index)

        # Step 3: Split turns into older (to compress) and recent (to preserve)
        older_turns = turn_logs[:split_index]
        recent_turns = turn_logs[split_index:]

        preserved_turns = []

        # Step 4: Handle compression of older turns
        if older_turns:
            # Check if first turn is already a compressed_history summary
            existing_summary = ""
            turns_to_compress = older_turns

            if older_turns[0].turn_id == "compressed_history":
                # Extract existing summary and remove from list
                existing_summary = older_turns[0].summary or ""
                turns_to_compress = older_turns[1:]

            # Compress the new batch (if any)
            if turns_to_compress:
                new_summary_turn = self.compress_turns_to_summary(turns_to_compress)

                # Merge with existing summary if present
                if existing_summary:
                    final_summary = f"{existing_summary}\n[...]\n{new_summary_turn.summary}"
                    new_summary_turn.summary = final_summary

                preserved_turns.append(new_summary_turn)
            elif existing_summary:
                # No new turns to compress, but preserve existing summary
                preserved_turns.append(older_turns[0])

        # Step 5: Add preserved recent turns
        preserved_turns.extend(recent_turns)

        # Step 6: Verify result fits in token budget
        result_messages = []
        for turn in preserved_turns:
            result_messages.extend(self._turn_to_messages(turn))

        result_tokens, _ = token_estimator(result_messages)

        # Step 7: Panic mode - if still over budget, keep only last turn + summary
        if result_tokens > target_tokens and len(preserved_turns) > 1:
            # Extract or create summary
            if preserved_turns[0].turn_id == "compressed_history":
                summary_turn = preserved_turns[0]
            else:
                # Create summary from all but last turn
                summary_turn = self.compress_turns_to_summary(preserved_turns[:-1])

            # Keep only summary + last turn
            preserved_turns = [summary_turn, preserved_turns[-1]]

        return preserved_turns

    def compress_turns_to_summary(self, turns: list[Turn]) -> Turn:
        """
        Compress multiple turns into a single summary turn.

        Handles incremental compression when compressed_history already exists.
        Ensures turn_id is always "compressed_history" for cache stability.

        Args:
            turns: Turns to compress

        Returns:
            Single summary Turn object with aggregated metadata
        """
        if not turns:
            return Turn(
                turn_id="compressed_history",
                start_time=datetime.now().isoformat(),
                events=[],
                summary="No turns to compress"
            )

        summary_parts = []
        files_modified = set()
        files_created = set()
        files_read = set()
        tools_used = set()

        for turn in turns:
            # Skip compressed_history turns (already summarized)
            if turn.turn_id == "compressed_history":
                continue

            if turn.summary:
                summary_parts.append(f"Turn {turn.turn_id}: {turn.summary}")
            else:
                summary_parts.append(f"Turn {turn.turn_id}: User interaction completed")

            # Consolidate file metadata
            files_modified.update(turn.files_modified)
            files_created.update(turn.files_created)
            files_read.update(turn.files_read)
            tools_used.update(turn.tools_used)

        # Create one summary turn for all older context
        # Ensure turn_id is always "compressed_history" for cache stability
        summary_turn = Turn(
            turn_id="compressed_history",
            start_time=turns[0].start_time if turns else datetime.now().isoformat(),
            events=[],  # Clear events list to save tokens
            end_time=turns[-1].end_time if turns else datetime.now().isoformat(),
            files_modified=list(files_modified),
            files_created=list(files_created),
            files_read=list(files_read),
            tools_used=list(tools_used),
            summary="; ".join(summary_parts) if summary_parts else "History compressed",
        )

        return summary_turn

    def _turn_to_messages(self, turn: Turn) -> list[dict[str, Any]]:
        """
        Convert turn to messages for token counting.

        Handles compressed_history turns specially by using assistant role
        to avoid system prompt conflicts (per user requirement).

        Args:
            turn: Turn to convert

        Returns:
            List of message dictionaries in API format
        """
        msgs = []

        if turn.turn_id == "compressed_history":
            # Use assistant role to avoid system prompt conflicts
            msgs.append({
                "role": "assistant",
                "content": f"[Context Summary - Prior Conversation]\n{turn.summary}"
            })
            return msgs

        # Normal turn processing - convert events to messages
        for event in turn.events:
            if event.type == "user_message":
                msgs.append({"role": "user", "content": event.content})
            elif event.type == "assistant_message":
                msgs.append({"role": "assistant", "content": event.content})
            elif event.type == "tool_response":
                msgs.append({"role": "tool", "content": event.result})

        return msgs

    def convert_messages_to_turns(
        self, messages: list[dict[str, Any]], turn_counter: int
    ) -> list[Turn]:
        """
        Convert message list to turn logs.

        Groups messages into turns based on user messages.

        Args:
            messages: List of messages to convert
            turn_counter: Starting turn counter

        Returns:
            List of Turn objects
        """
        turn_logs = []
        current_turn_events = []

        i = 0
        while i < len(messages):
            message = messages[i]

            # Defensive: Skip non-dict messages
            if not isinstance(message, dict):
                print(
                    f"WARNING: Non-dict message in convert_messages_to_turns at index {i}: {type(message)}"
                )
                i += 1
                continue

            role = message.get("role")
            content = message.get("content", "")

            if role == "system":
                # Skip system messages in turn conversion
                i += 1
                continue
            elif role == "user":
                # Start of a new turn
                if current_turn_events:
                    # Complete previous turn
                    turn_logs.append(
                        self._create_turn_from_events(current_turn_events, turn_counter)
                    )
                    turn_counter += 1

                # Start new turn
                current_turn_events = [TurnEvent(type="user_message", content=content)]
            elif role == "assistant":
                current_turn_events.append(TurnEvent(type="assistant_message", content=content))
            elif role == "tool":
                # Try to determine tool name from context or use generic
                tool_name = "unknown_tool"
                current_turn_events.append(
                    TurnEvent(type="tool_response", tool=tool_name, result=content)
                )

            i += 1

        # Complete the last turn if there are events
        if current_turn_events:
            turn_logs.append(self._create_turn_from_events(current_turn_events, turn_counter))

        return turn_logs

    def _create_turn_from_events(self, events: list[TurnEvent], turn_counter: int) -> Turn:
        """
        Create a turn from a list of events.

        Args:
            events: List of turn events
            turn_counter: Turn number

        Returns:
            Turn object
        """
        turn = Turn(
            turn_id=f"turn_{turn_counter:03d}",
            start_time=datetime.now().isoformat(),
            events=events,
            end_time=datetime.now().isoformat(),
            summary=self._generate_turn_summary_from_events(events),
        )

        return turn

    def _generate_turn_summary_from_events(self, events: list[TurnEvent]) -> str:
        """
        Generate a summary from turn events.

        Args:
            events: List of events to summarize

        Returns:
            Summary string
        """
        user_msgs = [e for e in events if e.type == "user_message"]
        assistant_msgs = [e for e in events if e.type == "assistant_message"]
        tool_calls = [e for e in events if e.type == "tool_call"]

        summary_parts = []

        if user_msgs:
            user_content = (
                user_msgs[0].content[:50] + "..."
                if len(user_msgs[0].content) > 50
                else user_msgs[0].content
            )
            summary_parts.append(f"User: {user_content}")

        if tool_calls:
            tools = list({e.tool for e in tool_calls if e.tool})
            summary_parts.append(f"Tools: {', '.join(tools)}")

        if assistant_msgs:
            summary_parts.append(f"Assistant responded ({len(assistant_msgs)} messages)")

        return "; ".join(summary_parts) if summary_parts else "Turn completed"
