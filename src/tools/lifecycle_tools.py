#!/usr/bin/env python3

"""
Lifecycle Tools for Grok Assistant

Provides task completion signaling for human-in-the-loop context management.
"""

from typing import Dict, Any
from .base import BaseTool, ToolResult
from ..core.config import Config


class TaskCompletionSignal(Exception):
    """Exception raised to signal task completion and trigger user interaction."""

    def __init__(self, summary: str, next_steps: str = ""):
        self.summary = summary
        self.next_steps = next_steps
        super().__init__(summary)


class TaskCompletedTool(BaseTool):
    """
    Tool for the agent to signal task completion.
    Triggers context management interaction if token usage is high.
    """

    def get_name(self) -> str:
        return "task_completed"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Signal task completion.

        Raises TaskCompletionSignal to trigger main loop interaction.

        Args:
            args: Tool arguments containing:
                - summary (str): Summary of what was accomplished
                - next_steps (str, optional): Suggestions for next steps
        """
        summary = args.get("summary", "Task completed.")
        next_steps = args.get("next_steps", "")

        # Validate summary is not empty
        if not summary or not summary.strip():
            summary = "Task completed."

        # Truncate very long summaries to prevent token waste
        if len(summary) > 500:
            summary = summary[:497] + "..."

        # Raise signal to be caught by main loop
        raise TaskCompletionSignal(summary, next_steps)


def create_lifecycle_tools(config: Config) -> list[BaseTool]:
    """Create lifecycle management tools."""
    return [TaskCompletedTool(config)]
