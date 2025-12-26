#!/usr/bin/env python3

"""
Application Context for Grok Assistant

Provides composition root for dependency injection, managing all application
dependencies in a single, testable container.

This eliminates global state and enables easy test setup with mock dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional

from xai_sdk import Client

from src.core.config import Config
from src.ui.adapter import UIProtocol, RichUIAdapter, MockUIAdapter
from src.ui import get_console, get_prompt_session


@dataclass
class AppContext:
    """
    Composition root that manages all application dependencies.

    This class serves as the single source of truth for all dependencies,
    enabling dependency injection throughout the application and simplifying
    testing with mock dependencies.

    Attributes:
        config: Application configuration
        client: xAI SDK client
        ui: UI adapter for display and user input
        command_registry: Optional command registry (set after creation)
        tool_executor: Optional tool executor (set after creation)
    """

    config: Config
    client: Client
    ui: UIProtocol
    command_registry: Optional[object] = None
    tool_executor: Optional[object] = None

    @classmethod
    def create_production(cls, config: Optional[Config] = None) -> 'AppContext':
        """
        Create production AppContext with real UI and services.

        This factory method creates an AppContext with:
        - Real Rich console UI
        - xAI client
        - Production configuration

        Args:
            config: Optional config to use. If not provided, creates new Config.

        Returns:
            AppContext configured for production use

        Example:
            >>> context = AppContext.create_production()
            >>> context.ui.show_info("Application started")
        """
        # Create or use provided config
        if config is None:
            config = Config()

        # Initialize xAI client
        client = Client()

        # Create production UI adapter
        console = get_console()
        prompt_session = get_prompt_session()
        ui = RichUIAdapter(console, prompt_session)

        return cls(
            config=config,
            client=client,
            ui=ui,
            command_registry=None,
            tool_executor=None
        )

    @classmethod
    def create_testing(
        cls,
        config: Optional[Config] = None,
        ui: Optional[UIProtocol] = None,
        client: Optional[Client] = None
    ) -> 'AppContext':
        """
        Create testing AppContext with mock UI and configurable dependencies.

        This factory method creates an AppContext suitable for testing:
        - Mock UI adapter (unless custom ui provided)
        - Mock client (unless custom client provided)
        - Test configuration (unless custom config provided)

        Args:
            config: Optional custom config. If not provided, creates new Config.
            ui: Optional custom UI adapter. If not provided, creates MockUIAdapter.
            client: Optional custom client. If not provided, creates mock client.

        Returns:
            AppContext configured for testing

        Example:
            >>> context = AppContext.create_testing()
            >>> context.ui.set_responses(["yes", "John"])
            >>> context.ui.show_info("Test message")
            >>> assert context.ui.get_messages_by_type("info") == ["Test message"]
        """
        # Create or use provided config
        if config is None:
            config = Config()

        # Create or use provided client (mock for testing)
        if client is None:
            # Create a mock client for testing (doesn't require API key)
            from unittest.mock import Mock
            client = Mock(spec=Client)

        # Create or use provided UI adapter
        if ui is None:
            ui = MockUIAdapter()

        return cls(
            config=config,
            client=client,
            ui=ui,
            command_registry=None,
            tool_executor=None
        )

    def set_command_registry(self, registry: object) -> None:
        """
        Set the command registry after creation.

        Args:
            registry: Command registry instance
        """
        self.command_registry = registry

    def set_tool_executor(self, executor: object) -> None:
        """
        Set the tool executor after creation.

        Args:
            executor: Tool executor instance
        """
        self.tool_executor = executor
