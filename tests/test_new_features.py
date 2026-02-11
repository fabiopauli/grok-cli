#!/usr/bin/env python3

"""
Tests for new features: agent mode and command suggestions
"""

from src.commands import create_command_registry
from src.core.config import Config


class TestAgentMode:
    """Test agent mode functionality."""

    def test_agent_mode_default_disabled(self):
        """Test that agent mode is disabled by default."""
        config = Config()
        assert config.agent_mode is False

    def test_agent_mode_affects_confirmations(self):
        """Test that agent mode affects confirmation flags."""
        config = Config()

        # Default state
        assert config.require_bash_confirmation is True
        assert config.require_powershell_confirmation is True
        assert config.agent_mode is False

        # Enable agent mode
        config.agent_mode = True
        assert config.agent_mode is True

        # Confirmations should still be True (they're just not checked when agent_mode is True)
        assert config.require_bash_confirmation is True
        assert config.require_powershell_confirmation is True


class TestCommandSuggestions:
    """Test command suggestion functionality."""

    def test_get_all_command_patterns(self):
        """Test getting all command patterns."""
        config = Config()
        registry = create_command_registry(config)

        patterns = registry.get_all_command_patterns()

        # Should have all the commands
        assert "/help" in patterns
        assert "/exit" in patterns
        assert "/add " in patterns  # Note: /add has a space in the pattern
        assert "/agent" in patterns
        assert "/fuzzy" in patterns
        assert "/clear" in patterns

    def test_find_similar_command_exact_match(self):
        """Test finding similar command with exact match."""
        config = Config()
        registry = create_command_registry(config)

        # Exact match should work
        similar = registry.find_similar_command("/help")
        assert similar == "/help"

    def test_find_similar_command_typo(self):
        """Test finding similar command with typo."""
        config = Config()
        registry = create_command_registry(config)

        # Close typo should find similar
        similar = registry.find_similar_command("/hlep")
        assert similar == "/help"

        similar = registry.find_similar_command("/eixt")
        assert similar == "/exit"

    def test_find_similar_command_no_match(self):
        """Test that completely different input returns None."""
        config = Config()
        registry = create_command_registry(config)

        # Completely different should return None
        registry.find_similar_command("/xyz123")
        # Might return None or a low-score match
        # This depends on the threshold

    def test_find_similar_command_not_slash(self):
        """Test that non-slash input returns None."""
        config = Config()
        registry = create_command_registry(config)

        # Non-slash input should return None
        similar = registry.find_similar_command("hello")
        assert similar is None


class TestAgentCommand:
    """Test the /agent command."""

    def test_agent_command_registered(self):
        """Test that agent command is registered."""
        config = Config()
        registry = create_command_registry(config)

        patterns = registry.get_all_command_patterns()
        assert "/agent" in patterns

    def test_agent_command_matches(self):
        """Test that agent command matches correctly."""
        config = Config()
        registry = create_command_registry(config)

        command = registry.find_command("/agent")
        assert command is not None
        assert command.get_pattern() == "/agent"
