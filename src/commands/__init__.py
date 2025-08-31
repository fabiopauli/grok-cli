"""
Command module for Grok Assistant

Contains command handlers implementing the command pattern.
"""

from .base import BaseCommand, CommandResult, CommandRegistry
from .system_commands import ExitCommand, ClearScreenCommand, ClearContextCommand, HelpCommand, OsCommand, FuzzyCommand
from .file_commands import AddCommand, RemoveCommand, FolderCommand
from .context_commands import ContextCommand, LogCommand, ReasonerCommand, OneTimeReasonerCommand, DefaultModelCommand, ContextModeCommand, SequentialContextCommand, SmartTruncationCommand, CoderCommand
from .memory_commands import MemoryCommand

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
    
    # File commands
    registry.register(AddCommand(config))
    registry.register(RemoveCommand(config))
    registry.register(FolderCommand(config))
    
    # Context commands
    registry.register(ContextCommand(config))
    registry.register(LogCommand(config))
    registry.register(ReasonerCommand(config))
    registry.register(OneTimeReasonerCommand(config))
    registry.register(DefaultModelCommand(config))
    registry.register(CoderCommand(config))
    registry.register(ContextModeCommand(config))
    registry.register(SequentialContextCommand(config))
    registry.register(SmartTruncationCommand(config))
    
    # Memory commands
    registry.register(MemoryCommand(config))
    
    return registry


__all__ = [
    'BaseCommand',
    'CommandResult', 
    'CommandRegistry',
    'create_command_registry'
]