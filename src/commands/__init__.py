"""
Command module for Grok Assistant

Contains command handlers implementing the command pattern.
"""

from .base import BaseCommand, CommandResult, CommandRegistry
from .system_commands import ExitCommand, ClearScreenCommand, ClearContextCommand, HelpCommand, OsCommand, FuzzyCommand, AgentCommand, MaxStepsCommand, JobsCommand, SelfModeCommand, ReloadToolsCommand
from .file_commands import AddCommand, RemoveCommand, FolderCommand
from .context_commands import (
    ContextCommand, LogCommand, ReasonerCommand, DefaultModelCommand,
    ContextModeCommand, SequentialContextCommand, SmartTruncationCommand,
    CoderCommand, Grok4Command, Grok4ReasonerCommand, MaxContextCommand
)
from .memory_commands import MemoryCommand
from .agentic_commands import PlanCommand, ImproveCommand, SpawnCommand, EpisodesCommand

from ..core.config import Config


def create_command_registry(config: Config) -> CommandRegistry:
    """
    Create and configure the command registry with all available commands.
    
    Args:
        config: Configuration object
        
    Returns:
        Configured CommandRegistry instance
    """
    registry = CommandRegistry(config)
    
    # System commands
    registry.register(ExitCommand(config))
    registry.register(ClearScreenCommand(config))
    registry.register(ClearContextCommand(config))
    registry.register(HelpCommand(config))
    registry.register(OsCommand(config))
    registry.register(FuzzyCommand(config))
    registry.register(AgentCommand(config))
    registry.register(MaxStepsCommand(config))
    registry.register(JobsCommand(config))
    registry.register(SelfModeCommand(config))
    registry.register(ReloadToolsCommand(config))

    # File commands
    registry.register(AddCommand(config))
    registry.register(RemoveCommand(config))
    registry.register(FolderCommand(config))
    
    # Context commands
    registry.register(ContextCommand(config))
    registry.register(LogCommand(config))
    registry.register(ReasonerCommand(config))
    registry.register(DefaultModelCommand(config))
    registry.register(CoderCommand(config))
    registry.register(Grok4Command(config))
    registry.register(Grok4ReasonerCommand(config))
    registry.register(MaxContextCommand(config))
    registry.register(ContextModeCommand(config))
    registry.register(SequentialContextCommand(config))
    registry.register(SmartTruncationCommand(config))

    # Memory commands
    registry.register(MemoryCommand(config))

    # Agentic reasoning commands
    registry.register(PlanCommand(config))
    registry.register(ImproveCommand(config))
    registry.register(SpawnCommand(config))
    registry.register(EpisodesCommand(config))

    return registry


__all__ = [
    'BaseCommand',
    'CommandResult', 
    'CommandRegistry',
    'create_command_registry'
]