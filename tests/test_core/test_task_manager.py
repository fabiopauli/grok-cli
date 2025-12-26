#!/usr/bin/env python3

"""
Tests for TaskManager (Phase 3: Task Tracking System)

Tests the task management functionality for AI todo lists.
"""

import pytest
from datetime import datetime

from src.core.task_manager import TaskManager, Task


class TestTaskCreation:
    """Test task creation and basic operations."""

    def test_add_task_with_defaults(self):
        """Test adding a task with default priority."""
        manager = TaskManager()
        task_id = manager.add_task("Test task")

        assert task_id is not None
        assert task_id.startswith("task_")
        assert len(task_id) == 13  # "task_" + 8 chars

    def test_add_task_with_priority(self):
        """Test adding tasks with different priorities."""
        manager = TaskManager()

        high_task = manager.add_task("High priority", priority="high")
        normal_task = manager.add_task("Normal priority", priority="normal")
        low_task = manager.add_task("Low priority", priority="low")

        assert high_task is not None
        assert normal_task is not None
        assert low_task is not None

    def test_add_task_empty_description_raises_error(self):
        """Test that empty description raises error."""
        manager = TaskManager()

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_task("")

        with pytest.raises(ValueError, match="cannot be empty"):
            manager.add_task("   ")

    def test_add_task_invalid_priority_raises_error(self):
        """Test that invalid priority raises error."""
        manager = TaskManager()

        with pytest.raises(ValueError, match="Invalid priority"):
            manager.add_task("Test task", priority="urgent")


class TestTaskStatusManagement:
    """Test task status transitions."""

    def test_start_task(self):
        """Test starting a task."""
        manager = TaskManager()
        task_id = manager.add_task("Test task")

        result = manager.start_task(task_id)
        assert result is True

        tasks = manager.list_tasks(show_completed=True)
        assert tasks[0].status == "in_progress"

    def test_complete_task(self):
        """Test completing a task."""
        manager = TaskManager()
        task_id = manager.add_task("Test task")

        result = manager.complete_task(task_id)
        assert result is True

        tasks = manager.list_tasks(show_completed=True)
        assert tasks[0].status == "completed"
        assert tasks[0].completed is not None

    def test_task_workflow(self):
        """Test full task workflow: add -> start -> complete."""
        manager = TaskManager()
        task_id = manager.add_task("Test task")

        # Initially pending
        tasks = manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].status == "pending"

        # Start task
        manager.start_task(task_id)
        tasks = manager.list_tasks()
        assert tasks[0].status == "in_progress"

        # Complete task
        manager.complete_task(task_id)
        tasks = manager.list_tasks(show_completed=True)
        assert tasks[0].status == "completed"

    def test_start_nonexistent_task(self):
        """Test starting a nonexistent task returns False."""
        manager = TaskManager()
        result = manager.start_task("task_notfound")
        assert result is False

    def test_complete_nonexistent_task(self):
        """Test completing a nonexistent task returns False."""
        manager = TaskManager()
        result = manager.complete_task("task_notfound")
        assert result is False


class TestTaskListing:
    """Test task listing and filtering."""

    def test_list_tasks_empty(self):
        """Test listing tasks when none exist."""
        manager = TaskManager()
        tasks = manager.list_tasks()
        assert len(tasks) == 0

    def test_list_tasks_excludes_completed_by_default(self):
        """Test that completed tasks are excluded by default."""
        manager = TaskManager()
        task1 = manager.add_task("Active task")
        task2 = manager.add_task("Completed task")
        manager.complete_task(task2)

        tasks = manager.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task1

    def test_list_tasks_include_completed(self):
        """Test listing all tasks including completed."""
        manager = TaskManager()
        manager.add_task("Active task")
        task2 = manager.add_task("Completed task")
        manager.complete_task(task2)

        tasks = manager.list_tasks(show_completed=True)
        assert len(tasks) == 2

    def test_list_tasks_filter_by_priority(self):
        """Test filtering tasks by priority."""
        manager = TaskManager()
        high_task = manager.add_task("High priority", priority="high")
        manager.add_task("Normal priority", priority="normal")
        manager.add_task("Low priority", priority="low")

        high_tasks = manager.list_tasks(priority="high")
        assert len(high_tasks) == 1
        assert high_tasks[0].id == high_task

    def test_list_tasks_sorted_by_created_time(self):
        """Test that tasks are sorted by creation time."""
        manager = TaskManager()
        task1 = manager.add_task("First task")
        task2 = manager.add_task("Second task")
        task3 = manager.add_task("Third task")

        tasks = manager.list_tasks()
        assert tasks[0].id == task1
        assert tasks[1].id == task2
        assert tasks[2].id == task3


class TestTaskRemoval:
    """Test task removal operations."""

    def test_remove_task(self):
        """Test removing a task."""
        manager = TaskManager()
        task_id = manager.add_task("Test task")

        result = manager.remove_task(task_id)
        assert result is True

        tasks = manager.list_tasks(show_completed=True)
        assert len(tasks) == 0

    def test_remove_nonexistent_task(self):
        """Test removing a nonexistent task returns False."""
        manager = TaskManager()
        result = manager.remove_task("task_notfound")
        assert result is False


class TestTaskClearing:
    """Test clearing tasks."""

    def test_clear_all_tasks(self):
        """Test clearing all tasks."""
        manager = TaskManager()
        manager.add_task("Task 1")
        manager.add_task("Task 2")
        manager.add_task("Task 3")

        count = manager.clear_tasks()
        assert count == 3

        tasks = manager.list_tasks(show_completed=True)
        assert len(tasks) == 0

    def test_clear_completed_only(self):
        """Test clearing only completed tasks."""
        manager = TaskManager()
        active_task = manager.add_task("Active task")
        completed_task = manager.add_task("Completed task")
        manager.complete_task(completed_task)

        count = manager.clear_tasks(clear_completed_only=True)
        assert count == 1

        tasks = manager.list_tasks(show_completed=True)
        assert len(tasks) == 1
        assert tasks[0].id == active_task


class TestTaskSummary:
    """Test task summary generation."""

    def test_get_summary_empty(self):
        """Test getting summary when no tasks exist."""
        manager = TaskManager()
        summary = manager.get_task_summary()
        assert summary == ""

    def test_get_summary_with_tasks(self):
        """Test getting summary with various task states."""
        manager = TaskManager()
        pending_task = manager.add_task("Pending task")
        in_progress_task = manager.add_task("In progress task")
        completed_task = manager.add_task("Completed task")

        manager.start_task(in_progress_task)
        manager.complete_task(completed_task)

        summary = manager.get_task_summary()

        assert "Active Tasks" in summary
        assert "1 pending" in summary
        assert "1 in progress" in summary
        assert "1 completed" in summary
        assert "Pending task" in summary
        assert "In progress task" in summary
        assert "Completed task" in summary

    def test_get_summary_shows_high_priority(self):
        """Test that high priority tasks are marked in summary."""
        manager = TaskManager()
        manager.add_task("High priority task", priority="high")

        summary = manager.get_task_summary()

        assert "High priority task" in summary
        assert "high" in summary or "🔴" in summary

    def test_get_summary_orders_by_status_and_priority(self):
        """Test that summary orders tasks correctly."""
        manager = TaskManager()
        manager.add_task("Low priority", priority="low")
        high_task = manager.add_task("High priority", priority="high")
        in_progress = manager.add_task("In progress")

        manager.start_task(in_progress)

        summary = manager.get_task_summary()

        # In-progress should come first
        in_progress_pos = summary.find("In progress")
        high_pos = summary.find("High priority")
        low_pos = summary.find("Low priority")

        assert in_progress_pos < high_pos
        assert high_pos < low_pos


class TestTaskCounts:
    """Test task counting functionality."""

    def test_get_task_count_empty(self):
        """Test getting counts when no tasks exist."""
        manager = TaskManager()
        counts = manager.get_task_count()

        assert counts["pending"] == 0
        assert counts["in_progress"] == 0
        assert counts["completed"] == 0
        assert counts["total"] == 0

    def test_get_task_count_with_tasks(self):
        """Test getting counts with various task states."""
        manager = TaskManager()
        task1 = manager.add_task("Pending 1")
        task2 = manager.add_task("Pending 2")
        task3 = manager.add_task("In progress")
        task4 = manager.add_task("Completed")

        manager.start_task(task3)
        manager.complete_task(task4)

        counts = manager.get_task_count()

        assert counts["pending"] == 2
        assert counts["in_progress"] == 1
        assert counts["completed"] == 1
        assert counts["total"] == 4


class TestTaskDataclass:
    """Test Task dataclass functionality."""

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task = Task(
            id="task_abc12345",
            description="Test task",
            status="pending",
            priority="normal",
            created=datetime.now(),
            completed=None,
        )

        task_dict = task.to_dict()

        assert task_dict["id"] == "task_abc12345"
        assert task_dict["description"] == "Test task"
        assert task_dict["status"] == "pending"
        assert task_dict["priority"] == "normal"
        assert task_dict["created"] is not None
        assert task_dict["completed"] is None

    def test_task_to_dict_with_completed(self):
        """Test converting completed task to dictionary."""
        task = Task(
            id="task_abc12345",
            description="Test task",
            status="completed",
            priority="normal",
            created=datetime.now(),
            completed=datetime.now(),
        )

        task_dict = task.to_dict()

        assert task_dict["completed"] is not None
