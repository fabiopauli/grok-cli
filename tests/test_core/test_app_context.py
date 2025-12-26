#!/usr/bin/env python3

"""
Tests for AppContext (Phase 2: Dependency Injection)

Tests the composition root that manages all application dependencies.
"""

import os
import pytest
from pathlib import Path

from src.core.app_context import AppContext
from src.core.config import Config
from src.ui.adapter import UIProtocol, RichUIAdapter, MockUIAdapter


# Skip production tests if no API key is set
requires_api_key = pytest.mark.skipif(
    not os.environ.get("XAI_API_KEY"),
    reason="XAI_API_KEY environment variable not set"
)


class TestAppContextCreation:
    """Test AppContext factory methods."""

    @requires_api_key
    def test_create_production_with_default_config(self):
        """Test creating production context with default config."""
        context = AppContext.create_production()

        assert context is not None
        assert context.config is not None
        assert context.client is not None
        assert context.ui is not None
        assert isinstance(context.ui, RichUIAdapter)
        assert context.command_registry is None  # Not set yet
        assert context.tool_executor is None  # Not set yet

    @requires_api_key
    def test_create_production_with_custom_config(self):
        """Test creating production context with custom config."""
        custom_config = Config()
        custom_config.current_model = "grok-4-1-fast-reasoning"

        context = AppContext.create_production(config=custom_config)

        assert context.config.current_model == "grok-4-1-fast-reasoning"
        assert isinstance(context.ui, RichUIAdapter)

    def test_create_testing_with_defaults(self):
        """Test creating testing context with default mock UI."""
        context = AppContext.create_testing()

        assert context is not None
        assert context.config is not None
        assert context.client is not None
        assert context.ui is not None
        assert isinstance(context.ui, MockUIAdapter)

    def test_create_testing_with_custom_config(self):
        """Test creating testing context with custom config."""
        custom_config = Config()
        custom_config.agent_mode = True

        context = AppContext.create_testing(config=custom_config)

        assert context.config.agent_mode is True
        assert isinstance(context.ui, MockUIAdapter)

    def test_create_testing_with_custom_ui(self):
        """Test creating testing context with custom UI adapter."""
        custom_ui = MockUIAdapter()
        custom_ui.set_responses(["test response"])

        context = AppContext.create_testing(ui=custom_ui)

        assert context.ui is custom_ui
        assert context.ui.prompt("Enter: ") == "test response"


class TestAppContextDependencyManagement:
    """Test dependency injection and management."""

    def test_set_command_registry(self):
        """Test setting command registry after creation."""
        context = AppContext.create_testing()

        # Create a mock registry
        mock_registry = {"type": "command_registry"}
        context.set_command_registry(mock_registry)

        assert context.command_registry == mock_registry

    def test_set_tool_executor(self):
        """Test setting tool executor after creation."""
        context = AppContext.create_testing()

        # Create a mock executor
        mock_executor = {"type": "tool_executor"}
        context.set_tool_executor(mock_executor)

        assert context.tool_executor == mock_executor

    def test_all_dependencies_set(self):
        """Test setting all dependencies."""
        context = AppContext.create_testing()

        mock_registry = {"type": "command_registry"}
        mock_executor = {"type": "tool_executor"}

        context.set_command_registry(mock_registry)
        context.set_tool_executor(mock_executor)

        assert context.config is not None
        assert context.client is not None
        assert context.ui is not None
        assert context.command_registry == mock_registry
        assert context.tool_executor == mock_executor


class TestAppContextUIAdapter:
    """Test UI adapter integration in AppContext."""

    def test_mock_ui_in_testing_context(self):
        """Test that testing context uses MockUIAdapter correctly."""
        context = AppContext.create_testing()

        # Should be able to use UI methods
        context.ui.show_info("Test message")

        # Verify message was recorded
        assert isinstance(context.ui, MockUIAdapter)
        messages = context.ui.get_messages_by_type("info")
        assert len(messages) == 1
        assert messages[0] == "Test message"

    @requires_api_key
    def test_production_ui_adapter(self):
        """Test that production context uses RichUIAdapter."""
        context = AppContext.create_production()

        # Should be RichUIAdapter
        assert isinstance(context.ui, RichUIAdapter)
        assert hasattr(context.ui, 'console')
        assert hasattr(context.ui, 'prompt_session')


class TestAppContextIntegration:
    """Integration tests for AppContext."""

    def test_context_with_config_modifications(self):
        """Test that config modifications work through AppContext."""
        context = AppContext.create_testing()

        # Modify config
        context.config.agent_mode = True
        context.config.current_model = "grok-4-1-fast-reasoning"

        # Verify changes
        assert context.config.agent_mode is True
        assert context.config.current_model == "grok-4-1-fast-reasoning"

    def test_testing_context_workflow(self):
        """Test typical testing workflow with AppContext."""
        # Create testing context
        context = AppContext.create_testing()

        # Set up mock UI responses
        context.ui.set_responses(["yes", "test input"])

        # Simulate command registry and tool executor
        context.set_command_registry({"commands": []})
        context.set_tool_executor({"tools": []})

        # Verify complete setup
        assert context.config is not None
        assert context.client is not None
        assert context.ui is not None
        assert context.command_registry is not None
        assert context.tool_executor is not None

        # Test UI interaction
        response1 = context.ui.prompt("Confirm: ")
        response2 = context.ui.prompt("Enter: ")
        assert response1 == "yes"
        assert response2 == "test input"
