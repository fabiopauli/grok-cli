#!/usr/bin/env python3

"""
Tests for Lifecycle Tools (Task Completion)

Tests the task completion signaling tool including:
- TaskCompletionSignal exception
- TaskCompletedTool execution
- Summary validation and truncation
"""

import pytest

from src.core.config import Config
from src.tools.lifecycle_tools import (
    TaskCompletedTool,
    TaskCompletionSignal,
    create_lifecycle_tools,
)


class TestTaskCompletionSignal:
    """Test TaskCompletionSignal exception."""

    def test_signal_creation_with_summary(self):
        """Test creating signal with summary."""
        signal = TaskCompletionSignal("Task completed successfully")

        assert signal.summary == "Task completed successfully"
        assert signal.next_steps == ""
        assert str(signal) == "Task completed successfully"

    def test_signal_creation_with_next_steps(self):
        """Test creating signal with next steps."""
        signal = TaskCompletionSignal(
            "Implemented feature X",
            "Consider adding tests for edge cases"
        )

        assert signal.summary == "Implemented feature X"
        assert signal.next_steps == "Consider adding tests for edge cases"

    def test_signal_is_exception(self):
        """Test that signal is an exception that can be raised."""
        signal = TaskCompletionSignal("Test")

        assert isinstance(signal, Exception)

        # Test it can be raised and caught
        with pytest.raises(TaskCompletionSignal) as exc_info:
            raise signal

        assert exc_info.value.summary == "Test"


class TestTaskCompletedTool:
    """Test TaskCompletedTool execution."""

    def test_tool_name(self):
        """Test tool name is correct."""
        config = Config()
        tool = TaskCompletedTool(config)

        assert tool.get_name() == "task_completed"

    def test_execute_with_summary(self):
        """Test executing tool with summary raises signal."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": "Feature implemented"})

        assert exc_info.value.summary == "Feature implemented"
        assert exc_info.value.next_steps == ""

    def test_execute_with_summary_and_next_steps(self):
        """Test executing tool with both summary and next steps."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({
                "summary": "Database schema updated",
                "next_steps": "Run migrations in production"
            })

        assert exc_info.value.summary == "Database schema updated"
        assert exc_info.value.next_steps == "Run migrations in production"

    def test_execute_with_empty_summary_uses_default(self):
        """Test that empty summary uses default."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": ""})

        assert exc_info.value.summary == "Task completed."

    def test_execute_with_whitespace_summary_uses_default(self):
        """Test that whitespace-only summary uses default."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": "   \n\t  "})

        assert exc_info.value.summary == "Task completed."

    def test_execute_truncates_very_long_summary(self):
        """Test that very long summaries are truncated."""
        config = Config()
        tool = TaskCompletedTool(config)

        long_summary = "x" * 600  # Exceeds 500 char limit

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": long_summary})

        # Should be truncated to 500 chars
        assert len(exc_info.value.summary) == 500
        assert exc_info.value.summary.endswith("...")

    def test_execute_without_summary_uses_default(self):
        """Test that missing summary uses default."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({})

        assert exc_info.value.summary == "Task completed."

    def test_execute_preserves_normal_length_summary(self):
        """Test that normal summaries are not modified."""
        config = Config()
        tool = TaskCompletedTool(config)

        summary = "Implemented user authentication with JWT tokens"

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": summary})

        assert exc_info.value.summary == summary

    def test_execute_with_next_steps_only_no_summary(self):
        """Test executing with next_steps but no summary."""
        config = Config()
        tool = TaskCompletedTool(config)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"next_steps": "Add more tests"})

        # Should use default summary
        assert exc_info.value.summary == "Task completed."
        assert exc_info.value.next_steps == "Add more tests"


class TestCreateLifecycleTools:
    """Test factory function for creating lifecycle tools."""

    def test_creates_tool_list(self):
        """Test that factory creates list of tools."""
        config = Config()
        tools = create_lifecycle_tools(config)

        assert isinstance(tools, list)
        assert len(tools) == 1
        assert isinstance(tools[0], TaskCompletedTool)

    def test_tools_have_correct_config(self):
        """Test that created tools have correct config."""
        config = Config()
        config.min_preserved_turns = 7  # Custom value
        tools = create_lifecycle_tools(config)

        assert tools[0].config.min_preserved_turns == 7


class TestToolIntegration:
    """Test tool integration with tool executor."""

    def test_tool_can_be_registered(self):
        """Test that tool can be registered with executor."""
        from src.tools import create_tool_executor

        config = Config()
        executor = create_tool_executor(config)

        # Tool should be registered
        assert "task_completed" in executor.tools

    def test_tool_execution_via_executor(self):
        """Test executing tool through executor."""
        import json

        from src.tools import create_tool_executor

        config = Config()
        executor = create_tool_executor(config)

        tool_call = {
            "function": {
                "name": "task_completed",
                "arguments": json.dumps({
                    "summary": "Test completed",
                    "next_steps": "Review results"
                })
            }
        }

        # Should raise TaskCompletionSignal
        with pytest.raises(TaskCompletionSignal) as exc_info:
            executor.execute_tool_call(tool_call)

        assert exc_info.value.summary == "Test completed"
        assert exc_info.value.next_steps == "Review results"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_summary_with_newlines_preserved(self):
        """Test that newlines in summary are preserved."""
        config = Config()
        tool = TaskCompletedTool(config)

        summary = "Task 1: Done\nTask 2: Done\nTask 3: Done"

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": summary})

        assert "\n" in exc_info.value.summary
        assert exc_info.value.summary == summary

    def test_summary_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        config = Config()
        tool = TaskCompletedTool(config)

        summary = "Implemented feature 🎉 with émojis and accénts"

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": summary})

        assert exc_info.value.summary == summary

    def test_summary_exactly_500_chars_not_truncated(self):
        """Test that summary of exactly 500 chars is not truncated."""
        config = Config()
        tool = TaskCompletedTool(config)

        summary = "x" * 500  # Exactly at limit

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": summary})

        # Should not be truncated (no "...")
        assert len(exc_info.value.summary) == 500
        assert not exc_info.value.summary.endswith("...")

    def test_summary_501_chars_truncated(self):
        """Test that summary of 501 chars is truncated."""
        config = Config()
        tool = TaskCompletedTool(config)

        summary = "x" * 501  # Just over limit

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({"summary": summary})

        # Should be truncated to 500 chars (497 + "...")
        assert len(exc_info.value.summary) == 500
        assert exc_info.value.summary.endswith("...")

    def test_next_steps_not_truncated(self):
        """Test that next_steps is not truncated."""
        config = Config()
        tool = TaskCompletedTool(config)

        # Very long next_steps
        next_steps = "y" * 1000

        with pytest.raises(TaskCompletionSignal) as exc_info:
            tool.execute({
                "summary": "Done",
                "next_steps": next_steps
            })

        # next_steps should be preserved as-is
        assert exc_info.value.next_steps == next_steps
        assert len(exc_info.value.next_steps) == 1000
