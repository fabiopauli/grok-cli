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

    def truncate_turns(
        self,
        turn_logs: list[Turn],
        target_tokens: int,
        token_estimator: Callable[[list[dict[str, Any]]], tuple[int, dict[str, int]]],
    ) -> list[Turn]:
        """
        Apply smart truncation to turn logs.

        Strategy: Keep only the most recent 2 turns in full detail,
        compress all older turns into a single summary turn.

        Args:
            turn_logs: List of turns to truncate
            target_tokens: Target token count after truncation
            token_estimator: Function to estimate tokens from messages

        Returns:
            Truncated list of turns
        """
        if len(turn_logs) <= 1:
            # Can't truncate further
            return turn_logs

        preserved_turns = []

        # Create a single compressed summary of all older turns
        # Keep only the most recent turn if we have more than 1
        older_turns = turn_logs[:-1]

        if older_turns:
            summary_turn = self.compress_turns_to_summary(older_turns)
            preserved_turns.append(summary_turn)

        # Keep only the most recent turn in full detail
        preserved_turns.extend(turn_logs[-1:])

        return preserved_turns

    def compress_turns_to_summary(self, turns: list[Turn]) -> Turn:
        """
        Compress multiple turns into a single summary turn.

        Args:
            turns: Turns to compress

        Returns:
            Single summary Turn object with aggregated metadata
        """
        summary_parts = []
        files_modified = set()
        files_created = set()
        files_read = set()
        tools_used = set()

        for turn in turns:
            if turn.summary:
                summary_parts.append(f"Turn {turn.turn_id}: {turn.summary}")
            else:
                summary_parts.append(f"Turn {turn.turn_id}: User interaction completed")

            files_modified.update(turn.files_modified)
            files_created.update(turn.files_created)
            files_read.update(turn.files_read)
            tools_used.update(turn.tools_used)

        # Create one summary turn for all older context
        summary_turn = Turn(
            turn_id="compressed_history",
            start_time=turns[0].start_time if turns else datetime.now().isoformat(),
            events=[],  # No detailed events in compressed turn
            end_time=turns[-1].end_time if turns else datetime.now().isoformat(),
            files_modified=list(files_modified),
            files_created=list(files_created),
            files_read=list(files_read),
            tools_used=list(tools_used),
            summary="; ".join(summary_parts),
        )

        return summary_turn

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
