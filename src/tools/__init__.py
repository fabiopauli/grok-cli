"""
Tools module for Grok Assistant

Contains tool execution handlers for AI function calls.
"""

from .base import BaseTool, ToolResult, ToolExecutor
from .file_tools import create_file_tools
from .shell_tools import create_shell_tools
from .memory_tool import MemoryTool, ListMemoriesTool, RemoveMemoryTool

from ..core.config import Config


def create_tool_executor(config: Config, memory_manager=None) -> ToolExecutor:
    """
    Create and configure the tool executor with all available tools.
    
    Args:
        config: Configuration object
        memory_manager: Memory manager instance (optional)
        
    Returns:
        Configured ToolExecutor instance
    """
    executor = ToolExecutor(config)
    
    # Register file tools
    for tool in create_file_tools(config):
        executor.register_tool(tool)
    
    # Register shell tools
    for tool in create_shell_tools(config):
        executor.register_tool(tool)
    
    # Register memory tools
    memory_tool = MemoryTool(config)
    list_memories_tool = ListMemoriesTool(config)
    remove_memory_tool = RemoveMemoryTool(config)
    
    # Set memory manager if provided
    if memory_manager:
        memory_tool.set_memory_manager(memory_manager)
        list_memories_tool.set_memory_manager(memory_manager)
        remove_memory_tool.set_memory_manager(memory_manager)
    
    executor.register_tool(memory_tool)
    executor.register_tool(list_memories_tool)
    executor.register_tool(remove_memory_tool)
    
    return executor


__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolExecutor',
    'create_tool_executor'
]