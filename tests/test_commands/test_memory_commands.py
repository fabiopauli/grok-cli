#!/usr/bin/env python3

"""
Tests for Memory Commands

Critical path tests for memory command handlers.
"""

import pytest

from src.commands.memory_commands import MemoryCommand


@pytest.fixture
def memory_command(mock_config):
    """Create a MemoryCommand for testing."""
    return MemoryCommand(mock_config)


def test_memory_command_pattern(memory_command):
    """Test MemoryCommand pattern."""
    assert memory_command.get_pattern() == "/memory"


def test_memory_command_description(memory_command):
    """Test MemoryCommand description."""
    description = memory_command.get_description()
    assert description is not None
    assert len(description) > 0


def test_memory_command_matches(memory_command):
    """Test MemoryCommand matches input."""
    assert memory_command.matches("/memory") is True
    assert memory_command.matches("/MEMORY") is True
    assert memory_command.matches("  /memory  ") is True
    assert memory_command.matches("/mem") is False
    assert memory_command.matches("memory") is False


def test_command_result_success():
    """Test CommandResult success factory."""
    from src.commands.base import CommandResult

    result = CommandResult.ok()

    assert result.success is True


def test_base_command_interface(mock_config):
    """Test BaseCommand interface."""
    from src.commands.base import BaseCommand

    class TestCommand(BaseCommand):
        def get_pattern(self):
            return "/test"

        def get_description(self):
            return "Test command"

        def matches(self, user_input):
            return user_input.startswith("/test")

        def execute(self, user_input, session):
            from src.commands.base import CommandResult

            return CommandResult.ok()

    cmd = TestCommand(mock_config)
    assert cmd.get_pattern() == "/test"
    assert cmd.get_description() == "Test command"
    assert cmd.matches("/test foo") is True
