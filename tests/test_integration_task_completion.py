#!/usr/bin/env python3

"""
Integration Tests for Task Completion Workflow

Tests the complete task completion workflow including:
- Task completion signal handling in main loop
- Context threshold-based interaction triggering
- User interaction prompts
- Context clearing vs preservation
"""

import json
from unittest.mock import Mock, patch

from src.core.tool_utils import handle_task_completion_interaction, handle_tool_calls
from src.core.config import Config
from src.core.session import GrokSession


class TestTaskCompletionInteraction:
    """Test handle_task_completion_interaction function."""

    def create_mock_session(self, token_count: int = 0):
        """Helper to create mock session with specific token count."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.config.task_completion_token_threshold = 128000

        # Mock context info
        session.get_context_info.return_value = {
            'estimated_tokens': token_count,
            'message_count': 10
        }

        session.clear_context = Mock()
        return session

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_below_threshold_just_acknowledges(self, mock_prompt, mock_console):
        """Test that below threshold only shows acknowledgment."""
        session = self.create_mock_session(token_count=50000)  # Below 128k

        console = Mock()
        mock_console.return_value = console

        result = handle_task_completion_interaction(
            session,
            "Feature implemented successfully"
        )

        # Should not prompt user
        assert result is False
        session.clear_context.assert_not_called()

        # Should print acknowledgment
        console.print.assert_any_call(
            "\n[green]✓ Task completed:[/green] Feature implemented successfully"
        )

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_below_threshold_shows_next_steps(self, mock_prompt, mock_console):
        """Test that next steps are shown when provided."""
        session = self.create_mock_session(token_count=50000)

        console = Mock()
        mock_console.return_value = console

        result = handle_task_completion_interaction(
            session,
            "Task done",
            "Consider adding tests"
        )

        assert result is False

        # Should print next steps
        console.print.assert_any_call(
            "[dim]Suggested next steps: Consider adding tests[/dim]\n"
        )

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_above_threshold_prompts_user(self, mock_prompt, mock_console):
        """Test that above threshold prompts user."""
        session = self.create_mock_session(token_count=150000)  # Above 128k

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "n"  # User says no
        mock_prompt.return_value = prompt_session

        handle_task_completion_interaction(
            session,
            "Large task completed"
        )

        # Should show threshold warning
        assert any(
            "Context usage:" in str(call)
            for call in console.print.call_args_list
        )

        # Should ask user
        prompt_session.prompt.assert_called_once()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_user_chooses_yes_clears_context(self, mock_prompt, mock_console):
        """Test that 'y' clears context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "y"
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(
            session,
            "Task done"
        )

        assert result is True
        session.clear_context.assert_called_once_with(keep_system_prompt=True)

        # Should show success message
        console.print.assert_any_call(
            "[green]✓ Context cleared. Memories and system prompt preserved.[/green]\n"
        )

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_user_chooses_yes_uppercase(self, mock_prompt, mock_console):
        """Test that 'Y' (uppercase) clears context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "Y"
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is True
        session.clear_context.assert_called_once()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_user_chooses_yes_full_word(self, mock_prompt, mock_console):
        """Test that 'yes' clears context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "yes"
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is True
        session.clear_context.assert_called_once()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_empty_input_defaults_to_yes(self, mock_prompt, mock_console):
        """Test that empty input (Enter) defaults to yes."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = ""  # User pressed Enter
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        # Empty should default to yes (clear context)
        assert result is True
        session.clear_context.assert_called_once()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_user_chooses_no_preserves_context(self, mock_prompt, mock_console):
        """Test that 'n' preserves context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "n"
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is False
        session.clear_context.assert_not_called()

        # Should show preservation message
        console.print.assert_any_call("[dim]Context preserved.[/dim]\n")

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_user_chooses_no_full_word(self, mock_prompt, mock_console):
        """Test that 'no' preserves context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "no"
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is False
        session.clear_context.assert_not_called()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_keyboard_interrupt_preserves_context(self, mock_prompt, mock_console):
        """Test that Ctrl+C preserves context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.side_effect = KeyboardInterrupt()
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is False
        session.clear_context.assert_not_called()

        # Should show keeping context message
        console.print.assert_any_call("\n[dim]Keeping context.[/dim]")

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_eof_error_preserves_context(self, mock_prompt, mock_console):
        """Test that EOF preserves context."""
        session = self.create_mock_session(token_count=150000)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.side_effect = EOFError()
        mock_prompt.return_value = prompt_session

        result = handle_task_completion_interaction(session, "Done")

        assert result is False
        session.clear_context.assert_not_called()

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_displays_token_count(self, mock_prompt, mock_console):
        """Test that token count is displayed to user."""
        session = self.create_mock_session(token_count=156789)

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "n"
        mock_prompt.return_value = prompt_session

        handle_task_completion_interaction(session, "Done")

        # Should display formatted token count
        printed_calls = [str(call) for call in console.print.call_args_list]
        assert any("156,789" in call for call in printed_calls)
        assert any("128,000" in call for call in printed_calls)  # Threshold


class TestHandleToolCallsIntegration:
    """Test handle_tool_calls function with TaskCompletionSignal."""

    def create_mock_response(self, tool_name: str, args: dict):
        """Helper to create mock response with tool call."""
        tool_call = Mock()
        tool_call.function.name = tool_name
        tool_call.function.arguments = json.dumps(args)

        response = Mock()
        response.tool_calls = [tool_call]
        return response

    @patch('src.core.tool_utils.handle_task_completion_interaction')
    @patch('src.ui.console.display_tool_call')
    @patch('src.core.tool_utils.get_console')
    def test_task_completed_signal_caught_and_handled(
        self, mock_console, mock_display, mock_interaction
    ):
        """Test that TaskCompletionSignal is caught and handled."""
        from src.tools import create_tool_executor

        # Setup
        config = Config()
        executor = create_tool_executor(config)
        session = Mock()
        session.add_message = Mock()

        console = Mock()
        mock_console.return_value = console

        mock_interaction.return_value = False

        # Create response with task_completed call
        response = self.create_mock_response(
            "task_completed",
            {"summary": "Test completed", "next_steps": "Review"}
        )

        # Execute
        results = handle_tool_calls(response, executor, session)

        # Verify signal was caught
        mock_interaction.assert_called_once()
        assert mock_interaction.call_args[0][1] == "Test completed"
        assert mock_interaction.call_args[0][2] == "Review"

        # Verify tool result was added to session
        session.add_message.assert_called_once()
        assert "Task completed" in session.add_message.call_args[0][1]

        # Verify result was returned
        assert len(results) == 1
        assert "Task completed" in results[0][1]

    @patch('src.core.tool_utils.handle_task_completion_interaction')
    @patch('src.ui.console.display_tool_call')
    @patch('src.core.tool_utils.get_console')
    def test_multiple_tools_with_task_completed(
        self, mock_console, mock_display, mock_interaction
    ):
        """Test handling multiple tools where one is task_completed."""
        from src.tools import create_tool_executor

        config = Config()
        executor = create_tool_executor(config)
        session = Mock()
        session.add_message = Mock()
        session.mount_file = Mock()

        console = Mock()
        mock_console.return_value = console

        mock_interaction.return_value = False

        # Create response with multiple tool calls
        response = Mock()

        # First tool: read_file (normal)
        tool1 = Mock()
        tool1.function.name = "read_file"
        tool1.function.arguments = json.dumps({"file_path": "test.txt"})

        # Second tool: task_completed (raises signal)
        tool2 = Mock()
        tool2.function.name = "task_completed"
        tool2.function.arguments = json.dumps({"summary": "Done"})

        response.tool_calls = [tool1, tool2]

        # Execute - should handle both tools
        # Note: This might fail if read_file actually tries to read
        # In real scenario, we'd mock the file system
        # For this test, we expect task_completed to be handled
        try:
            handle_tool_calls(response, executor, session)
        except Exception:
            # read_file might fail, but task_completed should still be caught
            pass

        # Verify interaction was triggered
        mock_interaction.assert_called_once()


class TestConfigurationIntegration:
    """Test that configuration values are respected."""

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_custom_threshold_respected(self, mock_prompt, mock_console):
        """Test that custom token threshold is respected."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.config.task_completion_token_threshold = 200000  # Custom threshold

        session.get_context_info.return_value = {
            'estimated_tokens': 150000  # Between default and custom
        }

        console = Mock()
        mock_console.return_value = console

        # Should be below custom threshold - no prompt
        result = handle_task_completion_interaction(session, "Done")

        assert result is False
        console.print.assert_any_call(
            "\n[green]✓ Task completed:[/green] Done"
        )

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_threshold_zero_always_prompts(self, mock_prompt, mock_console):
        """Test that threshold of 0 always prompts."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.config.task_completion_token_threshold = 0

        session.get_context_info.return_value = {
            'estimated_tokens': 100  # Any value
        }

        console = Mock()
        mock_console.return_value = console

        prompt_session = Mock()
        prompt_session.prompt.return_value = "n"
        mock_prompt.return_value = prompt_session

        # Should always prompt when threshold is 0
        handle_task_completion_interaction(session, "Done")

        prompt_session.prompt.assert_called_once()


class TestEdgeCases:
    """Test edge cases in the workflow."""

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_empty_summary_handled(self, mock_prompt, mock_console):
        """Test that empty summary is handled gracefully."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.get_context_info.return_value = {'estimated_tokens': 50000}

        console = Mock()
        mock_console.return_value = console

        # Should not crash with empty summary
        result = handle_task_completion_interaction(session, "")

        assert result is False
        # Should still print something
        assert console.print.called

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_very_long_summary_displayed(self, mock_prompt, mock_console):
        """Test that very long summaries are displayed."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.get_context_info.return_value = {'estimated_tokens': 50000}

        console = Mock()
        mock_console.return_value = console

        long_summary = "x" * 1000

        handle_task_completion_interaction(session, long_summary)

        # Should display the long summary
        printed = str(console.print.call_args_list)
        assert long_summary in printed

    @patch('src.core.tool_utils.get_console')
    @patch('src.core.tool_utils.get_prompt_session')
    def test_unicode_in_summary(self, mock_prompt, mock_console):
        """Test that Unicode characters in summary work."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.get_context_info.return_value = {'estimated_tokens': 50000}

        console = Mock()
        mock_console.return_value = console

        summary = "Task done 🎉 with émojis"

        handle_task_completion_interaction(session, summary)

        # Should handle Unicode
        printed = str(console.print.call_args_list)
        assert "🎉" in printed or "emojis" in printed
