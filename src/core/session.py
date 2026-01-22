#!/usr/bin/env python3

"""
Session management for Grok Assistant

Centralizes conversation state and chat instance management with dependency injection.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path

# Third-party imports
from xai_sdk import Client
from xai_sdk.chat import user, system, assistant, tool_result

# Local imports
from .config import Config
from .context_manager import ContextManager, ContextMode
from .memory_manager import MemoryManager
from .task_manager import TaskManager
from .episodic_memory import EpisodicMemoryManager


class GrokSession:
    """
    Centralized session management for Grok conversations.
    
    Enhanced with turn-based context management and persistent memory system.
    Provides dual-mode operation and directory-aware memory storage.
    """
    
    def __init__(self, client: Client, config: Config, tool_executor=None):
        """
        Initialize a new Grok session.

        Args:
            client: xAI client instance
            config: Configuration object (dependency injection)
            tool_executor: Tool executor instance (optional)
        """
        self.client = client
        self.config = config
        self.tool_executor = tool_executor
        self.model = config.current_model
        self.is_reasoner = config.is_reasoner
        self._use_reasoner_next = False
        
        # Initialize new turn-based and memory systems
        self.memory_manager = MemoryManager(config)
        self.episodic_memory = EpisodicMemoryManager(config)
        self.task_manager = TaskManager()
        self.context_manager = ContextManager(config)

        # Set memories in context manager (flat + episodic)
        memories = self.memory_manager.get_memories_for_context()
        episodes = self.episodic_memory.get_episodes_for_context(limit=3)
        self.context_manager.set_memories(memories)
        # Store episodes separately for now
        self._recent_episodes = episodes

        # Add initial context
        self._add_initial_context()
        
        # Create chat instance
        self.chat_instance = self._create_chat_instance_from_context()
        
        # Track if we need to rebuild chat (for model changes)
        self._needs_rebuild = False

    @property
    def history(self) -> List[Dict[str, Any]]:
        """
        Backward-compatible facade: derives from context manager.
        Ensures legacy code still works during migration.
        """
        return self.context_manager.get_context_for_api()

    def _add_initial_context(self) -> None:
        """Add initial project and environment context to conversation."""
        # Add directory structure
        dir_summary = self._get_directory_tree_summary(self.config.base_dir)
        self.context_manager.add_system_message(
            f"Project directory structure at startup:\n\n{dir_summary}"
        )
        
        # Add OS and shell info
        shell_status = ", ".join([f"{shell}({'✓' if available else '✗'})" 
                                 for shell, available in self.config.os_info['shell_available'].items()])
        self.context_manager.add_system_message(
            f"Runtime environment: {self.config.os_info['system']} {self.config.os_info['release']}, "
            f"Python {self.config.os_info['python_version']}, Shells: {shell_status}"
        )
        
        # System prompt is now handled by context manager
        # No need to add to legacy history
    
    def _get_directory_tree_summary(self, base_dir: Path) -> str:
        """Get a summary of directory tree structure."""
        # Import here to avoid circular imports
        from ..utils.path_utils import get_directory_tree_summary
        return get_directory_tree_summary(base_dir, self.config)
    
    def _create_chat_instance_from_context(self):
        """Create chat instance from context manager."""
        return self._create_chat_instance(self.model)
    
    def _create_chat_instance(self, model: str):
        """Create a chat instance with the specified model."""
        chat = self.client.chat.create(model=model, tools=self.config.get_tools())
        
        # Get context from context manager
        context_messages = self.context_manager.get_context_for_api()
        
        for message in context_messages:
            if message["role"] == "system":
                chat.append(system(message["content"]))
            elif message["role"] == "user":
                chat.append(user(message["content"]))
            elif message["role"] == "assistant":
                chat.append(assistant(message["content"]))
            elif message["role"] == "tool":
                chat.append(tool_result(message["content"]))
        
        return chat
    
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """
        Add a message to the conversation history (legacy method).
        
        Args:
            role: Message role ('user', 'assistant', 'system', 'tool')
            content: Message content
            **kwargs: Additional message properties (e.g., tool_calls, tool_call_id)
        """
        # For backward compatibility, delegate to context manager
        if role == "user":
            self.start_turn(content)
        elif role == "assistant":
            tool_calls = kwargs.get("tool_calls")
            self.context_manager.add_assistant_message(content, tool_calls)
        elif role == "tool":
            # For tool messages, we need the tool name - try to extract or use default
            tool_name = kwargs.get("tool_name", "unknown_tool")
            self.context_manager.add_tool_response(tool_name, content)
        elif role == "system":
            self.context_manager.add_system_message(content)

        # Note: history is now a read-only property derived from context_manager

        # Add to chat instance following xAI SDK patterns
        if role == "user":
            # User messages already added by start_turn, don't duplicate
            pass
        elif role == "assistant":
            # Assistant messages are added via append(response) in get_response()
            pass
        elif role == "tool":
            # Add tool results to chat instance
            from xai_sdk.chat import tool_result
            self.chat_instance.append(tool_result(content))
        elif role == "system":
            # System messages need to be added to chat instance
            from xai_sdk.chat import system
            self.chat_instance.append(system(content))
    
    def switch_model(self, new_model: str) -> None:
        """
        Switch to a different model.

        Args:
            new_model: Model name to switch to
        """
        if new_model != self.model:
            # Import here to avoid circular imports
            from ..ui.console import get_console
            console = get_console()

            console.print(f"[dim]Model changed to {new_model}, creating new chat...[/dim]")
            self.model = new_model
            self.is_reasoner = new_model == self.config.reasoner_model
            self.config.set_model(new_model)
            self.chat_instance = self._create_chat_instance_from_context()

    def refresh_context_limits(self) -> None:
        """
        Refresh the context limits after config changes.

        This recreates the chat instance with updated context limits
        while preserving the conversation history.
        """
        # Recreate chat instance with updated config
        self.chat_instance = self._create_chat_instance_from_context()

    def get_response(self, use_reasoner: bool = False) -> Any:
        """
        Get a response from the current model.

        Args:
            use_reasoner: If True, use reasoner model for this response only

        Returns:
            Response object from the chat API
        """
        # Lazy rebuild: If mounted files changed, rebuild chat instance
        if self._needs_rebuild:
            self.chat_instance = self._create_chat_instance_from_context()
            self._needs_rebuild = False

        # Update task summary in context manager
        task_summary = self.task_manager.get_task_summary()
        self.context_manager.set_task_summary(task_summary)

        # Check context usage and apply automatic management
        self._manage_context()

        # Check if we should use reasoner for this response
        should_use_reasoner = use_reasoner or self._use_reasoner_next
        
        # Use reasoner for one-off response if requested
        if should_use_reasoner and self.model != self.config.reasoner_model:
            # Create temporary reasoner chat instance
            temp_chat = self._create_chat_instance(self.config.reasoner_model)
            response = temp_chat.sample()
        else:
            # Get response from current chat instance
            response = self.chat_instance.sample()
        
        # Reset the one-time reasoner flag
        self._use_reasoner_next = False
        
        # Append response to chat instance (as per xAI SDK documentation)
        # This is the correct pattern according to xAI docs
        if not should_use_reasoner or self.model == self.config.reasoner_model:
            # Only append if using the main chat instance (not temp reasoner chat)
            self.chat_instance.append(response)
        
        return response
    
    def _manage_context(self) -> None:
        """Manage context size and apply truncation if needed."""
        # Context management is now handled by the context manager
        # This method is kept for backward compatibility
        pass
    
    def update_working_directory(self, new_base_dir: Path) -> None:
        """
        Update the working directory context and refresh system prompt.
        
        Args:
            new_base_dir: New base directory path
        """
        # Update config with new base directory
        self.config.set_base_dir(new_base_dir)

        # Update the system prompt with new working directory context
        new_system_prompt = self.config.get_system_prompt()

        # Update the first message (system prompt) in history
        if self.history and self.history[0]["role"] == "system":
            self.history[0]["content"] = new_system_prompt

        # Get directory summary once for reuse (Performance fix)
        dir_summary = self._get_directory_tree_summary(new_base_dir)

        # Add directory change notification to conversation context
        self.add_message("system", f"Working directory changed to: {new_base_dir}\n\nNew directory structure:\n\n{dir_summary}")

        # Update memory manager with new directory
        memory_info = self.memory_manager.change_directory(new_base_dir)

        # Update context manager with new memories
        memories = self.memory_manager.get_memories_for_context()
        self.context_manager.set_memories(memories)

        # Add directory change notification to context manager (reuse dir_summary)
        self.context_manager.add_system_message(
            f"Working directory changed to: {new_base_dir}\n\nNew directory structure:\n\n{dir_summary}"
        )
        
        # Rebuild chat instance to include updated context
        self.chat_instance = self._create_chat_instance_from_context()
        
        return memory_info
    
    def clear_context(self, keep_system_prompt: bool = True) -> None:
        """
        Clear conversation context.

        Args:
            keep_system_prompt: Whether to keep the system prompt
        """
        # Clear context manager
        self.context_manager.clear_context(keep_memories=True)

        # Note: self.history is now a read-only property derived from context_manager
        # No need to clear it separately - it's automatically updated via the @property

        # Re-add initial context
        self._add_initial_context()

        # Rebuild chat instance
        self.chat_instance = self._create_chat_instance_from_context()
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get current context usage information."""
        return self.context_manager.get_context_stats()
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get a copy of the conversation history."""
        # Return context from context manager
        return self.context_manager.get_context_for_api()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information."""
        return {
            "current_model": self.model,
            "is_reasoner": self.is_reasoner,
            "model_name": "Grok-4" if self.is_reasoner else "Grok-3"
        }
    
    def enable_fuzzy_mode(self) -> None:
        """Enable fuzzy matching for the current session."""
        self.config.fuzzy_enabled_by_default = True
        self.add_message("system", "Fuzzy matching enabled for file operations in this session.")
    
    def disable_fuzzy_mode(self) -> None:
        """Disable fuzzy matching for the current session."""
        self.config.fuzzy_enabled_by_default = False
        self.add_message("system", "Fuzzy matching disabled for file operations in this session.")
    
    # New turn-based methods
    
    def start_turn(self, user_message: str) -> str:
        """
        Start a new conversation turn.
        
        Args:
            user_message: User message that starts the turn
            
        Returns:
            Turn ID for the new turn
        """
        # Add user message to chat instance (xAI SDK pattern)
        from xai_sdk.chat import user
        self.chat_instance.append(user(user_message))
        
        # Also delegate to context manager for memory tracking
        return self.context_manager.start_turn(user_message)
    
    def add_assistant_response(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Add an assistant response to the current turn.
        
        Args:
            content: Assistant response content
            tool_calls: Optional tool calls made by the assistant
        """
        self.context_manager.add_assistant_message(content, tool_calls)
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """
        Add a tool call to the current turn.
        
        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
        """
        self.context_manager.add_tool_call(tool_name, args)
    
    def add_tool_result(self, tool_name: str, result: str) -> None:
        """
        Add a tool result to the current turn.
        
        Args:
            tool_name: Name of the tool
            result: Tool execution result
        """
        self.context_manager.add_tool_response(tool_name, result)
    
    def complete_turn(self, summary: Optional[str] = None) -> Optional[Any]:
        """
        Complete the current turn.
        
        Args:
            summary: Optional summary of what was accomplished
            
        Returns:
            The completed turn if one was active
        """
        return self.context_manager.complete_turn(summary)
    
    def set_context_mode(self, mode: str) -> None:
        """
        Set the context management mode.
        
        Args:
            mode: Context mode ('cache_optimized' or 'smart_truncation')
        """
        if mode == "cache_optimized":
            self.context_manager.set_mode(ContextMode.CACHE_OPTIMIZED)
        elif mode == "smart_truncation":
            self.context_manager.set_mode(ContextMode.SMART_TRUNCATION)
        else:
            raise ValueError(f"Invalid context mode: {mode}")
    
    def get_context_mode(self) -> str:
        """Get the current context management mode."""
        return self.context_manager.get_mode().value
    
    def get_memory_manager(self) -> MemoryManager:
        """Get the memory manager instance."""
        return self.memory_manager

    def get_episodic_memory(self) -> EpisodicMemoryManager:
        """Get the episodic memory manager instance."""
        return self.episodic_memory
    
    def handle_directory_memory_prompt(self, new_directory: Path) -> Dict[str, Any]:
        """
        Handle memory prompts when changing directories.

        Args:
            new_directory: New directory being switched to

        Returns:
            Dictionary with memory information and prompts
        """
        has_memories = self.memory_manager.has_directory_memories(new_directory)

        return {
            "has_existing_memories": has_memories,
            "memory_count": len(self.memory_manager.get_directory_memories(new_directory)) if has_memories else 0,
            "should_prompt_user": True
        }

    # Layered Context Model - File Mounting

    def mount_file(self, path: str, content: str) -> None:
        """
        Mount a file into the context. Mounted files persist across truncations.

        Args:
            path: File path to mount
            content: File content
        """
        self.context_manager.mount_file(path, content)
        # Mark that we need to rebuild chat instance
        self._needs_rebuild = True

    def unmount_file(self, path: str) -> bool:
        """
        Remove a file from the mounted context.

        Args:
            path: File path to unmount

        Returns:
            True if file was mounted and removed, False otherwise
        """
        result = self.context_manager.unmount_file(path)
        if result:
            # Mark that we need to rebuild chat instance
            self._needs_rebuild = True
        return result

    def get_mounted_files(self) -> Dict[str, Any]:
        """
        Get all currently mounted files.

        Returns:
            Dictionary of path -> FileContext for all mounted files
        """
        return self.context_manager.get_mounted_files()