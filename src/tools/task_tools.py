#!/usr/bin/env python3

"""
Task Management Tools for Grok Assistant

Provides AI-facing tools to manage internal todo lists during multi-step operations.

These tools enable the AI to:
- Break down complex work into trackable tasks
- Remember what needs to be done across multiple turns
- Show progress to users
- Ensure all steps are completed
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..core.task_manager import TaskManager


class AddTaskTool(BaseTool):
    """Tool for adding tasks to the task list."""

    def __init__(self, config: Config, task_manager: TaskManager):
        """
        Initialize the add task tool.

        Args:
            config: Configuration object
            task_manager: Task manager instance
        """
        super().__init__(config)
        self.task_manager = task_manager

    def get_name(self) -> str:
        """Get the tool name."""
        return "add_task"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Add a new task to the task list.

        Args:
            args: Dictionary with keys:
                - description (str): Task description
                - priority (str, optional): Task priority (low, normal, high)

        Returns:
            ToolResult with task ID or error message
        """
        try:
            description = args.get("description")
            if not description:
                return ToolResult.fail("Error: 'description' parameter is required")

            priority = args.get("priority", "normal")

            # Validate priority
            if priority not in ["low", "normal", "high"]:
                return ToolResult.fail(
                    f"Error: Invalid priority '{priority}'. Must be 'low', 'normal', or 'high'"
                )

            # Add task
            task_id = self.task_manager.add_task(description, priority=priority)

            return ToolResult.ok(
                f"Task added successfully.\n"
                f"Task ID: {task_id}\n"
                f"Description: {description}\n"
                f"Priority: {priority}\n"
                f"Status: pending"
            )

        except ValueError as e:
            return ToolResult.fail(f"Error adding task: {str(e)}")
        except Exception as e:
            return ToolResult.fail(f"Unexpected error adding task: {str(e)}")


class CompleteTaskTool(BaseTool):
    """Tool for marking tasks as completed."""

    def __init__(self, config: Config, task_manager: TaskManager):
        """
        Initialize the complete task tool.

        Args:
            config: Configuration object
            task_manager: Task manager instance
        """
        super().__init__(config)
        self.task_manager = task_manager

    def get_name(self) -> str:
        """Get the tool name."""
        return "complete_task"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Mark a task as completed.

        Args:
            args: Dictionary with keys:
                - task_id (str): Task ID to complete

        Returns:
            ToolResult with success message or error
        """
        try:
            task_id = args.get("task_id")
            if not task_id:
                return ToolResult.fail("Error: 'task_id' parameter is required")

            # Complete the task
            success = self.task_manager.complete_task(task_id)

            if success:
                return ToolResult.ok(f"Task {task_id} marked as completed ✓")
            else:
                return ToolResult.fail(f"Error: Task {task_id} not found")

        except Exception as e:
            return ToolResult.fail(f"Unexpected error completing task: {str(e)}")


class ListTasksTool(BaseTool):
    """Tool for listing tasks."""

    def __init__(self, config: Config, task_manager: TaskManager):
        """
        Initialize the list tasks tool.

        Args:
            config: Configuration object
            task_manager: Task manager instance
        """
        super().__init__(config)
        self.task_manager = task_manager

    def get_name(self) -> str:
        """Get the tool name."""
        return "list_tasks"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        List tasks, optionally filtered.

        Args:
            args: Dictionary with keys:
                - show_completed (bool, optional): Include completed tasks
                - priority (str, optional): Filter by priority

        Returns:
            ToolResult with task list
        """
        try:
            show_completed = args.get("show_completed", False)
            priority = args.get("priority")

            # Validate priority if provided
            if priority and priority not in ["low", "normal", "high"]:
                return ToolResult.fail(
                    f"Error: Invalid priority '{priority}'. Must be 'low', 'normal', or 'high'"
                )

            # Get tasks
            tasks = self.task_manager.list_tasks(
                show_completed=show_completed, priority=priority
            )

            if not tasks:
                filter_desc = ""
                if priority:
                    filter_desc = f" with priority '{priority}'"
                if show_completed:
                    return ToolResult.ok(f"No tasks found{filter_desc}.")
                else:
                    return ToolResult.ok(f"No active tasks found{filter_desc}.")

            # Format task list
            result = "Task List:\n"
            result += "=" * 60 + "\n\n"

            for task in tasks:
                status_icon = {
                    "pending": "○",
                    "in_progress": "▶",
                    "completed": "✓",
                }.get(task.status, "?")

                priority_marker = ""
                if task.priority == "high":
                    priority_marker = " 🔴"
                elif task.priority == "low":
                    priority_marker = " (low)"

                result += f"{status_icon} [{task.status}] {task.description}{priority_marker}\n"
                result += f"   ID: {task.id}\n"
                result += f"   Created: {task.created.strftime('%Y-%m-%d %H:%M:%S')}\n"

                if task.completed:
                    result += (
                        f"   Completed: {task.completed.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )

                result += "\n"

            # Add summary
            counts = self.task_manager.get_task_count()
            result += "=" * 60 + "\n"
            result += f"Total: {counts['total']} tasks "
            result += f"({counts['pending']} pending, {counts['in_progress']} in progress, {counts['completed']} completed)"

            return ToolResult.ok(result)

        except Exception as e:
            return ToolResult.fail(f"Unexpected error listing tasks: {str(e)}")


class RemoveTaskTool(BaseTool):
    """Tool for removing tasks from the task list."""

    def __init__(self, config: Config, task_manager: TaskManager):
        """
        Initialize the remove task tool.

        Args:
            config: Configuration object
            task_manager: Task manager instance
        """
        super().__init__(config)
        self.task_manager = task_manager

    def get_name(self) -> str:
        """Get the tool name."""
        return "remove_task"

    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Remove a task from the task list.

        Args:
            args: Dictionary with keys:
                - task_id (str): Task ID to remove

        Returns:
            ToolResult with success message or error
        """
        try:
            task_id = args.get("task_id")
            if not task_id:
                return ToolResult.fail("Error: 'task_id' parameter is required")

            # Remove the task
            success = self.task_manager.remove_task(task_id)

            if success:
                return ToolResult.ok(f"Task {task_id} removed successfully")
            else:
                return ToolResult.fail(f"Error: Task {task_id} not found")

        except Exception as e:
            return ToolResult.fail(f"Unexpected error removing task: {str(e)}")


def create_task_tools(config: Config, task_manager: TaskManager) -> list[BaseTool]:
    """
    Create all task management tools.

    Args:
        config: Configuration object
        task_manager: Task manager instance

    Returns:
        List of task management tools
    """
    return [
        AddTaskTool(config, task_manager),
        CompleteTaskTool(config, task_manager),
        ListTasksTool(config, task_manager),
        RemoveTaskTool(config, task_manager),
    ]
