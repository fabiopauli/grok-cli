#!/usr/bin/env python3

"""
Task Management for Grok Assistant

Provides task tracking capabilities for AI to maintain internal todo lists
during multi-step operations. Tasks are session-scoped and cleared with /clear.

This enables the AI to:
- Break down complex work into trackable tasks
- Remember what needs to be done across multiple turns
- Show progress to users
- Ensure all steps are completed
"""

import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Literal

from src.utils.logging_config import get_logger

logger = get_logger("task_manager")

# Type aliases for better type hints
TaskStatus = Literal["pending", "in_progress", "completed"]
TaskPriority = Literal["low", "normal", "high"]


@dataclass
class Task:
    """
    Represents a single task in the task list.

    Attributes:
        id: Unique task identifier (format: "task_XXXXXXXX")
        description: Human-readable task description
        status: Current task status (pending, in_progress, completed)
        priority: Task priority (low, normal, high)
        created: When the task was created
        completed: When the task was completed (None if not completed)
    """

    id: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created: datetime
    completed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert task to dictionary for serialization."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created": self.created.isoformat(),
            "completed": self.completed.isoformat() if self.completed else None,
        }


class TaskManager:
    """
    Manages tasks for AI assistant during multi-step operations.

    Tasks are stored in-memory and scoped to the current session.
    They are cleared when the user runs /clear command.

    Example:
        >>> manager = TaskManager()
        >>> task_id = manager.add_task("Read config file", priority="high")
        >>> manager.start_task(task_id)
        >>> manager.complete_task(task_id)
        >>> summary = manager.get_task_summary()
    """

    def __init__(self):
        """Initialize task manager with empty task list."""
        self._tasks: dict[str, Task] = {}
        logger.debug("TaskManager initialized")

    def _generate_task_id(self) -> str:
        """
        Generate unique task ID.

        Returns:
            Task ID in format "task_XXXXXXXX"
        """
        chars = string.ascii_lowercase + string.digits
        random_suffix = "".join(random.choices(chars, k=8))
        return f"task_{random_suffix}"

    def add_task(
        self, description: str, priority: TaskPriority = "normal"
    ) -> str:
        """
        Add a new task to the task list.

        Args:
            description: Task description
            priority: Task priority (low, normal, high)

        Returns:
            Task ID

        Example:
            >>> task_id = manager.add_task("Fix bug in parser", priority="high")
        """
        if not description or not description.strip():
            raise ValueError("Task description cannot be empty")

        if priority not in ["low", "normal", "high"]:
            raise ValueError(f"Invalid priority: {priority}")

        task_id = self._generate_task_id()
        task = Task(
            id=task_id,
            description=description.strip(),
            status="pending",
            priority=priority,
            created=datetime.now(),
        )

        self._tasks[task_id] = task
        logger.info(f"Added task {task_id}: {description} (priority: {priority})")

        return task_id

    def start_task(self, task_id: str) -> bool:
        """
        Mark a task as in progress.

        Args:
            task_id: Task ID to start

        Returns:
            True if successful, False if task not found

        Example:
            >>> manager.start_task("task_abc12345")
        """
        if task_id not in self._tasks:
            logger.warning(f"Cannot start task {task_id}: not found")
            return False

        task = self._tasks[task_id]
        task.status = "in_progress"
        logger.info(f"Started task {task_id}: {task.description}")

        return True

    def complete_task(self, task_id: str) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID to complete

        Returns:
            True if successful, False if task not found

        Example:
            >>> manager.complete_task("task_abc12345")
        """
        if task_id not in self._tasks:
            logger.warning(f"Cannot complete task {task_id}: not found")
            return False

        task = self._tasks[task_id]
        task.status = "completed"
        task.completed = datetime.now()
        logger.info(f"Completed task {task_id}: {task.description}")

        return True

    def remove_task(self, task_id: str) -> bool:
        """
        Remove a task from the task list.

        Args:
            task_id: Task ID to remove

        Returns:
            True if successful, False if task not found

        Example:
            >>> manager.remove_task("task_abc12345")
        """
        if task_id not in self._tasks:
            logger.warning(f"Cannot remove task {task_id}: not found")
            return False

        task = self._tasks.pop(task_id)
        logger.info(f"Removed task {task_id}: {task.description}")

        return True

    def list_tasks(
        self,
        show_completed: bool = False,
        priority: Optional[TaskPriority] = None,
    ) -> List[Task]:
        """
        List tasks, optionally filtered by status and priority.

        Args:
            show_completed: Include completed tasks in results
            priority: Filter by priority (low, normal, high)

        Returns:
            List of tasks matching filters

        Example:
            >>> # Get all pending/in-progress tasks
            >>> active_tasks = manager.list_tasks()
            >>> # Get all high priority tasks including completed
            >>> high_priority = manager.list_tasks(show_completed=True, priority="high")
        """
        tasks = list(self._tasks.values())

        # Filter by status
        if not show_completed:
            tasks = [t for t in tasks if t.status != "completed"]

        # Filter by priority
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]

        # Sort by created time
        tasks.sort(key=lambda t: t.created)

        return tasks

    def clear_tasks(self, clear_completed_only: bool = False) -> int:
        """
        Clear tasks from the task list.

        Args:
            clear_completed_only: If True, only clear completed tasks

        Returns:
            Number of tasks cleared

        Example:
            >>> # Clear only completed tasks
            >>> count = manager.clear_tasks(clear_completed_only=True)
            >>> # Clear all tasks
            >>> count = manager.clear_tasks()
        """
        if clear_completed_only:
            completed_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status == "completed"
            ]
            for task_id in completed_ids:
                del self._tasks[task_id]
            count = len(completed_ids)
            logger.info(f"Cleared {count} completed tasks")
        else:
            count = len(self._tasks)
            self._tasks.clear()
            logger.info(f"Cleared all {count} tasks")

        return count

    def get_task_summary(self) -> str:
        """
        Get a concise summary of current tasks for AI context.

        Returns:
            Human-readable summary string, or empty string if no tasks

        Example:
            >>> summary = manager.get_task_summary()
            >>> print(summary)
            Active Tasks (3 pending, 1 in progress, 2 completed):
            - [pending] Fix bug in parser (high priority)
            - [in_progress] Write tests
            - [pending] Update documentation
        """
        if not self._tasks:
            return ""

        tasks = list(self._tasks.values())
        pending = [t for t in tasks if t.status == "pending"]
        in_progress = [t for t in tasks if t.status == "in_progress"]
        completed = [t for t in tasks if t.status == "completed"]

        # Build summary header
        parts = []
        if pending:
            parts.append(f"{len(pending)} pending")
        if in_progress:
            parts.append(f"{len(in_progress)} in progress")
        if completed:
            parts.append(f"{len(completed)} completed")

        summary = f"Active Tasks ({', '.join(parts)}):\n"

        # List in-progress tasks first (most important)
        for task in in_progress:
            priority_marker = f" (🔴 {task.priority})" if task.priority == "high" else ""
            summary += f"- [▶ in_progress] {task.description}{priority_marker}\n"

        # Then pending tasks by priority
        high_priority = [t for t in pending if t.priority == "high"]
        normal_priority = [t for t in pending if t.priority == "normal"]
        low_priority = [t for t in pending if t.priority == "low"]

        for task in high_priority:
            summary += f"- [pending] {task.description} (🔴 high)\n"
        for task in normal_priority:
            summary += f"- [pending] {task.description}\n"
        for task in low_priority:
            summary += f"- [pending] {task.description} (low)\n"

        # Finally completed tasks (less important, but shows progress)
        for task in completed:
            summary += f"- [✓ completed] {task.description}\n"

        return summary.strip()

    def get_task_count(self) -> dict[str, int]:
        """
        Get task counts by status.

        Returns:
            Dictionary with counts for each status

        Example:
            >>> counts = manager.get_task_count()
            >>> print(counts)
            {'pending': 3, 'in_progress': 1, 'completed': 2, 'total': 6}
        """
        tasks = list(self._tasks.values())
        return {
            "pending": sum(1 for t in tasks if t.status == "pending"),
            "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
            "completed": sum(1 for t in tasks if t.status == "completed"),
            "total": len(tasks),
        }
