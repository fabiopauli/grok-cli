#!/usr/bin/env python3

"""
Tests for MaxContextCommand toggle functionality
"""

from unittest.mock import Mock, patch

from src.commands.context_commands import MaxContextCommand
from src.core.config import Config
from src.core.session import GrokSession


class TestMaxContextToggle:
    """Test /max command toggle functionality."""

    def create_mock_session(self, extended_context_enabled: bool = False):
        """Helper to create mock session."""
        session = Mock(spec=GrokSession)
        session.config = Config()
        session.config.use_extended_context = extended_context_enabled
        session.config.update_extended_context = Mock()
        session.refresh_context_limits = Mock()
        return session

    @patch('src.ui.console.get_console')
    def test_toggle_enables_extended_context(self, mock_console):
        """Test that /max enables extended context when disabled."""
        console = Mock()
        mock_console.return_value = console

        session = self.create_mock_session(extended_context_enabled=False)
        command = MaxContextCommand(session.config)

        command.execute("/max", session)

        # Should call update_extended_context with True
        session.config.update_extended_context.assert_called_once_with(True)

        # Should refresh session limits
        session.refresh_context_limits.assert_called_once()

        # Should print enabling message
        printed_calls = [str(call) for call in console.print.call_args_list]
        assert any("enabled" in call.lower() for call in printed_calls)
        assert any("2m" in call.lower() for call in printed_calls)

    @patch('src.ui.console.get_console')
    def test_toggle_disables_extended_context(self, mock_console):
        """Test that /max disables extended context when enabled."""
        console = Mock()
        mock_console.return_value = console

        session = self.create_mock_session(extended_context_enabled=True)
        command = MaxContextCommand(session.config)

        command.execute("/max", session)

        # Should call update_extended_context with False
        session.config.update_extended_context.assert_called_once_with(False)

        # Should refresh session limits
        session.refresh_context_limits.assert_called_once()

        # Should print disabling message
        printed_calls = [str(call) for call in console.print.call_args_list]
        assert any("disabled" in call.lower() for call in printed_calls)
        assert any("128k" in call.lower() for call in printed_calls)

    @patch('src.ui.console.get_console')
    def test_multiple_toggles(self, mock_console):
        """Test multiple toggles work correctly."""
        console = Mock()
        mock_console.return_value = console

        session = self.create_mock_session(extended_context_enabled=False)
        command = MaxContextCommand(session.config)

        # First toggle: enable
        command.execute("/max", session)
        assert session.config.update_extended_context.call_args_list[0][0][0]

        # Simulate state change
        session.config.use_extended_context = True

        # Second toggle: disable
        command.execute("/max", session)
        assert not session.config.update_extended_context.call_args_list[1][0][0]

        # Simulate state change
        session.config.use_extended_context = False

        # Third toggle: enable again
        command.execute("/max", session)
        assert session.config.update_extended_context.call_args_list[2][0][0]

    @patch('src.ui.console.get_console')
    def test_shows_warning_when_enabling(self, mock_console):
        """Test that warning about pricing is shown when enabling."""
        console = Mock()
        mock_console.return_value = console

        session = self.create_mock_session(extended_context_enabled=False)
        command = MaxContextCommand(session.config)

        command.execute("/max", session)

        # Should show pricing warning
        printed_calls = [str(call) for call in console.print.call_args_list]
        assert any("charged" in call.lower() or "rate" in call.lower() for call in printed_calls)

    @patch('src.ui.console.get_console')
    def test_shows_config_saved_message(self, mock_console):
        """Test that config saved message is shown."""
        console = Mock()
        mock_console.return_value = console

        session = self.create_mock_session(extended_context_enabled=False)
        command = MaxContextCommand(session.config)

        command.execute("/max", session)

        # Should show config saved message
        printed_calls = [str(call) for call in console.print.call_args_list]
        assert any("config" in call.lower() and "saved" in call.lower() for call in printed_calls)

    def test_matches_command(self):
        """Test that command matches /max."""
        config = Config()
        command = MaxContextCommand(config)

        assert command.matches("/max")
        assert command.matches("/MAX")
        assert command.matches("  /max  ")
        assert not command.matches("/maximum")
        assert not command.matches("max")

    def test_get_pattern(self):
        """Test command pattern."""
        config = Config()
        command = MaxContextCommand(config)

        assert command.get_pattern() == "/max"

    def test_get_description(self):
        """Test command description mentions toggle."""
        config = Config()
        command = MaxContextCommand(config)

        description = command.get_description()
        assert "toggle" in description.lower() or "2m" in description.lower()
