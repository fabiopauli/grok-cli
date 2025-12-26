"""
Tools module for Grok Assistant

Contains tool execution handlers for AI function calls.
"""

from .base import BaseTool, ToolResult, ToolExecutor
from .file_tools import create_file_tools
from .shell_tools import create_shell_tools
from .memory_tool import MemoryTool, ListMemoriesTool, RemoveMemoryTool
from .search_tool import create_search_tools
from .inspector_tool import create_inspector_tools
from .editor_tool import create_editor_tools
from .task_tools import create_task_tools
from .code_execution_tool import create_code_execution_tools
from .dynamic_tools import create_dynamic_tools, DynamicToolLoader
from .tool_registry import ToolRegistry

from ..core.config import Config


def create_tool_executor(config: Config, memory_manager=None, task_manager=None) -> ToolExecutor:
    """
    Create and configure the tool executor with all available tools.

    Args:
        config: Configuration object
        memory_manager: Memory manager instance (optional)
        task_manager: Task manager instance (optional)

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

    # Register search tools
    for tool in create_search_tools(config):
        executor.register_tool(tool)

    # Register inspector tools
    for tool in create_inspector_tools(config):
        executor.register_tool(tool)

    # Register editor tools
    for tool in create_editor_tools(config):
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

    # Register task tools if task_manager is provided
    if task_manager:
        for tool in create_task_tools(config, task_manager):
            executor.register_tool(tool)

    # Register code execution reminder tool
    for tool in create_code_execution_tools(config):
        executor.register_tool(tool)

    # Register dynamic tools if self-mode is enabled
    if getattr(config, 'self_mode', False):
        dynamic_tools, loader = create_dynamic_tools(config)
        for tool in dynamic_tools:
            executor.register_tool(tool)
        # Store loader reference for /reload-tools command
        config._dynamic_loader = loader

    return executor


__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolExecutor',
    'create_tool_executor'
]