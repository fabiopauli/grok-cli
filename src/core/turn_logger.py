#!/usr/bin/env python3

"""
Turn Logger for Grok Assistant

Handles clean sequential logging of conversation turns with minimal timestamps
and comprehensive event tracking for context management.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import Config


@dataclass
class TurnEvent:
    """Single event within a conversation turn."""
    type: str  # user_message, assistant_message, tool_call, tool_response
    content: str | None = None
    tool: str | None = None
    args: dict[str, Any] | None = None
    result: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.type:
            result["type"] = self.type
        if self.content is not None:
            result["content"] = self.content
        if self.tool is not None:
            result["tool"] = self.tool
        if self.args is not None:
            result["args"] = self.args
        if self.result is not None:
            result["result"] = self.result
        return result


@dataclass
class Turn:
    """Complete conversation turn with events and metadata."""
    turn_id: str
    start_time: str
    events: list[TurnEvent]
    end_time: str | None = None
    files_modified: list[str] | None = None
    files_created: list[str] | None = None
    files_read: list[str] | None = None
    tools_used: list[str] | None = None
    summary: str | None = None

    def __post_init__(self):
        """Initialize tracking sets if not provided."""
        if self.files_modified is None:
            self.files_modified = []
        if self.files_created is None:
            self.files_created = []
        if self.files_read is None:
            self.files_read = []
        if self.tools_used is None:
            self.tools_used = []

    def to_dict(self) -> dict[str, Any]:
        """Convert turn to dictionary for JSON serialization."""
        return {
            "turn_id": self.turn_id,
            "start_time": self.start_time,
            "events": [event.to_dict() for event in self.events],
            "end_time": self.end_time,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "files_read": self.files_read,
            "tools_used": self.tools_used,
            "summary": self.summary
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Turn':
        """Create Turn from dictionary."""
        events = [TurnEvent(**event_data) for event_data in data.get("events", [])]
        return cls(
            turn_id=data["turn_id"],
            start_time=data["start_time"],
            events=events,
            end_time=data.get("end_time"),
            files_modified=data.get("files_modified", []),
            files_created=data.get("files_created", []),
            files_read=data.get("files_read", []),
            tools_used=data.get("tools_used", []),
            summary=data.get("summary")
        )


class TurnLogger:
    """
    Manages conversation turn logging with clean event tracking.

    Handles turn boundaries, event sequencing, and file operation tracking
    for efficient context management and summarization.
    """

    def __init__(self, config: Config):
        """
        Initialize the turn logger.

        Args:
            config: Configuration object
        """
        self.config = config
        self.current_turn: Turn | None = None
        self._turn_counter = 0

    def start_turn(self, user_message: str) -> str:
        """
        Start a new conversation turn.

        Args:
            user_message: Initial user message that starts the turn

        Returns:
            Turn ID for the new turn
        """
        if self.current_turn is not None:
            raise RuntimeError("Cannot start new turn while another turn is active")

        self._turn_counter += 1
        turn_id = f"turn_{self._turn_counter:03d}"

        # Create new turn with user message
        self.current_turn = Turn(
            turn_id=turn_id,
            start_time=datetime.now().isoformat(),
            events=[TurnEvent(type="user_message", content=user_message)]
        )

        return turn_id

    def add_assistant_message(self, content: str) -> None:
        """
        Add an assistant message to the current turn.

        Args:
            content: Assistant message content
        """
        if self.current_turn is None:
            raise RuntimeError("No active turn to add assistant message to")

        event = TurnEvent(type="assistant_message", content=content)
        self.current_turn.events.append(event)

    def add_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        """
        Add a tool call to the current turn.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool
        """
        if self.current_turn is None:
            raise RuntimeError("No active turn to add tool call to")

        event = TurnEvent(type="tool_call", tool=tool_name, args=args)
        self.current_turn.events.append(event)

        # Track tool usage
        if tool_name not in self.current_turn.tools_used:
            self.current_turn.tools_used.append(tool_name)

    def add_tool_response(self, tool_name: str, result: str) -> None:
        """
        Add a tool response to the current turn.

        Args:
            tool_name: Name of the tool that generated the response
            result: Tool execution result
        """
        if self.current_turn is None:
            raise RuntimeError("No active turn to add tool response to")

        event = TurnEvent(type="tool_response", tool=tool_name, result=result)
        self.current_turn.events.append(event)

        # Track file operations based on tool and result
        self._track_file_operations(tool_name, result)

    def _track_file_operations(self, tool_name: str, result: str) -> None:
        """
        Track file operations based on tool usage.

        Args:
            tool_name: Name of the tool
            result: Tool result to analyze for file operations
        """
        if self.current_turn is None:
            return

        # Extract file paths from common file operations
        if tool_name in ["read_file", "read_multiple_files"]:
            # For read operations, try to extract file paths from the result
            self._extract_file_paths_from_read(result)

        elif tool_name in ["create_file", "create_multiple_files"]:
            # For create operations, mark files as created
            self._extract_file_paths_from_create(result)

        elif tool_name in ["edit_file"]:
            # For edit operations, mark files as modified
            self._extract_file_paths_from_edit(result)

    def _extract_file_paths_from_read(self, result: str) -> None:
        """Extract file paths from read operation results."""
        # This is a simplified implementation
        # In practice, you might want more sophisticated parsing
        if "File:" in result or "Reading file:" in result:
            # Try to extract file path from result
            lines = result.split('\n')
            for line in lines:
                if line.strip().startswith("File:") or line.strip().startswith("Reading file:"):
                    # Extract file path (this is simplified)
                    parts = line.split(':')
                    if len(parts) > 1:
                        file_path = parts[1].strip()
                        if file_path and file_path not in self.current_turn.files_read:
                            self.current_turn.files_read.append(file_path)

    def _extract_file_paths_from_create(self, result: str) -> None:
        """Extract file paths from create operation results."""
        if "created" in result.lower() or "Created" in result:
            # This is simplified - in practice, you'd parse the actual file paths
            # from the tool arguments or result
            pass

    def _extract_file_paths_from_edit(self, result: str) -> None:
        """Extract file paths from edit operation results."""
        if "edited" in result.lower() or "modified" in result.lower():
            # This is simplified - in practice, you'd parse the actual file paths
            # from the tool arguments or result
            pass

    def track_file_operation(self, operation: str, file_path: str) -> None:
        """
        Manually track a file operation.

        Args:
            operation: Type of operation (read, create, modify)
            file_path: Path to the file
        """
        if self.current_turn is None:
            return

        if operation == "read" and file_path not in self.current_turn.files_read:
            self.current_turn.files_read.append(file_path)
        elif operation == "create" and file_path not in self.current_turn.files_created:
            self.current_turn.files_created.append(file_path)
        elif operation == "modify" and file_path not in self.current_turn.files_modified:
            self.current_turn.files_modified.append(file_path)

    def complete_turn(self, summary: str | None = None) -> Turn:
        """
        Complete the current turn and return it.

        Args:
            summary: Optional summary of what was accomplished in the turn

        Returns:
            The completed turn
        """
        if self.current_turn is None:
            raise RuntimeError("No active turn to complete")

        # Set end time and summary
        self.current_turn.end_time = datetime.now().isoformat()
        if summary:
            self.current_turn.summary = summary
        else:
            self.current_turn.summary = self._generate_auto_summary()

        # Return completed turn and clear current
        completed_turn = self.current_turn
        self.current_turn = None

        return completed_turn

    def _generate_auto_summary(self) -> str:
        """Generate an automatic summary of the turn."""
        if self.current_turn is None:
            return "No active turn"

        # Count different types of events
        user_messages = len([e for e in self.current_turn.events if e.type == "user_message"])
        len([e for e in self.current_turn.events if e.type == "assistant_message"])
        len([e for e in self.current_turn.events if e.type == "tool_call"])

        # Build summary based on what happened
        parts = []

        if user_messages > 0:
            user_event = next(e for e in self.current_turn.events if e.type == "user_message")
            user_text = user_event.content[:50] + "..." if len(user_event.content) > 50 else user_event.content
            parts.append(f"User: {user_text}")

        if self.current_turn.tools_used:
            parts.append(f"Tools used: {', '.join(self.current_turn.tools_used)}")

        if self.current_turn.files_modified:
            parts.append(f"Modified: {', '.join(self.current_turn.files_modified)}")

        if self.current_turn.files_created:
            parts.append(f"Created: {', '.join(self.current_turn.files_created)}")

        return "; ".join(parts) if parts else "Turn completed"

    def get_current_turn(self) -> Turn | None:
        """Get the current active turn."""
        return self.current_turn

    def is_turn_active(self) -> bool:
        """Check if there's an active turn."""
        return self.current_turn is not None

    def get_turn_events_as_messages(self) -> list[dict[str, Any]]:
        """
        Convert current turn events to message format for API calls.

        Returns:
            List of messages in API format
        """
        if self.current_turn is None:
            return []

        messages = []
        for event in self.current_turn.events:
            if event.type == "user_message":
                messages.append({"role": "user", "content": event.content})
            elif event.type == "assistant_message":
                messages.append({"role": "assistant", "content": event.content})
            elif event.type == "tool_response":
                messages.append({"role": "tool", "content": event.result})

        return messages

    def get_all_messages_from_turns(self, completed_turns: list[Turn]) -> list[dict[str, Any]]:
        """
        Derive all messages from completed turns.
        This is the single source of truth for message history.

        Args:
            completed_turns: List of completed Turn objects

        Returns:
            List of messages in API format (role, content)
        """
        messages = []
        for turn in completed_turns:
            for event in turn.events:
                if event.type == "user_message":
                    messages.append({"role": "user", "content": event.content})
                elif event.type == "assistant_message":
                    messages.append({"role": "assistant", "content": event.content})
                elif event.type == "tool_response":
                    messages.append({"role": "tool", "content": event.result})
        return messages
