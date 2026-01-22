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
from .lifecycle_tools import create_lifecycle_tools, TaskCompletionSignal
from .planning_tool import create_planning_tools
from .multiagent_tool import create_multiagent_tools
from .orchestrator_tool import create_orchestrator_tools

from ..core.config import Config


def create_tool_executor(config: Config, memory_manager=None, task_manager=None, context_manager=None, client=None) -> ToolExecutor:
    """
    Create and configure the tool executor with all available tools.

    Args:
        config: Configuration object
        memory_manager: Memory manager instance (optional)
        task_manager: Task manager instance (optional)
        context_manager: Context manager instance (optional)
        client: xAI client for planning tools (optional)

    Returns:
        Configured ToolExecutor instance
    """
    executor = ToolExecutor(config)

    # Register file tools
    for tool in create_file_tools(config):
        # Set context manager if provided (fixes stale mount problem)
        if context_manager:
            tool.set_context_manager(context_manager)
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
        # Store reference for reflection tool
        config._memory_manager = memory_manager

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

    # Register lifecycle tools (task completion signaling)
    for tool in create_lifecycle_tools(config):
        executor.register_tool(tool)

    # Register planning and reflection tools
    for tool in create_planning_tools(config, client):
        executor.register_tool(tool)

    # Register multi-agent coordination tools
    for tool in create_multiagent_tools(config):
        executor.register_tool(tool)

    # Register orchestrator tools
    for tool in create_orchestrator_tools(config, client):
        executor.register_tool(tool)

    # Register dynamic tools if self-mode is enabled
    if getattr(config, 'self_mode', False):
        # Create a ToolRegistry that wraps the executor for unified registration
        # This ensures DynamicToolLoader registers into the central registry
        # rather than modifying the executor directly
        registry = ToolRegistry(config)
        registry._executor = executor  # Use the same executor we've been building

        # Pass the registry to DynamicToolLoader for centralized registration
        dynamic_tools, loader = create_dynamic_tools(config, registry=registry)
        for tool in dynamic_tools:
            executor.register_tool(tool)

        # Store loader and registry references for /reload-tools command
        config._dynamic_loader = loader
        config._tool_registry = registry

    return executor


def create_tool_registry(config: Config, memory_manager=None, task_manager=None, context_manager=None, client=None) -> ToolRegistry:
    """
    Create a unified ToolRegistry with all available tools.

    This is the preferred way to create tools when you want centralized
    management of both tool schemas (for API) and executors (for runtime).
    The ToolRegistry maintains a single source of truth for all capabilities.

    Args:
        config: Configuration object
        memory_manager: Memory manager instance (optional)
        task_manager: Task manager instance (optional)
        context_manager: Context manager instance (optional)
        client: xAI client for planning tools (optional)

    Returns:
        Configured ToolRegistry instance
    """
    registry = ToolRegistry(config)

    # Get the executor from the registry
    executor = registry.get_executor()

    # Register all tools with the executor (schema registration is separate)
    # Note: Static tools get schemas from config.get_tools()

    # Register file tools
    for tool in create_file_tools(config):
        if context_manager:
            tool.set_context_manager(context_manager)
        registry.register_tool(tool)

    # Register shell tools
    for tool in create_shell_tools(config):
        registry.register_tool(tool)

    # Register search tools
    for tool in create_search_tools(config):
        registry.register_tool(tool)

    # Register inspector tools
    for tool in create_inspector_tools(config):
        registry.register_tool(tool)

    # Register editor tools
    for tool in create_editor_tools(config):
        registry.register_tool(tool)

    # Register memory tools
    memory_tool = MemoryTool(config)
    list_memories_tool = ListMemoriesTool(config)
    remove_memory_tool = RemoveMemoryTool(config)

    if memory_manager:
        memory_tool.set_memory_manager(memory_manager)
        list_memories_tool.set_memory_manager(memory_manager)
        remove_memory_tool.set_memory_manager(memory_manager)
        config._memory_manager = memory_manager

    registry.register_tool(memory_tool)
    registry.register_tool(list_memories_tool)
    registry.register_tool(remove_memory_tool)

    # Register task tools
    if task_manager:
        for tool in create_task_tools(config, task_manager):
            registry.register_tool(tool)

    # Register code execution tools
    for tool in create_code_execution_tools(config):
        registry.register_tool(tool)

    # Register lifecycle tools
    for tool in create_lifecycle_tools(config):
        registry.register_tool(tool)

    # Register planning tools
    for tool in create_planning_tools(config, client):
        registry.register_tool(tool)

    # Register multi-agent tools
    for tool in create_multiagent_tools(config):
        registry.register_tool(tool)

    # Register orchestrator tools
    for tool in create_orchestrator_tools(config, client):
        registry.register_tool(tool)

    # Register dynamic tools with the registry for centralized management
    if getattr(config, 'self_mode', False):
        dynamic_tools, loader = create_dynamic_tools(config, registry=registry)
        for tool in dynamic_tools:
            registry.register_tool(tool)
        config._dynamic_loader = loader
        config._tool_registry = registry

    return registry


__all__ = [
    'BaseTool',
    'ToolResult',
    'ToolExecutor',
    'ToolRegistry',
    'TaskCompletionSignal',
    'create_tool_executor',
    'create_tool_registry'
]