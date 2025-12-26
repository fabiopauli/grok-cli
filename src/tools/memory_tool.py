#!/usr/bin/env python3

"""
Memory Tool for Grok Assistant

Provides save_memory function for storing persistent information that survives
context truncation and directory changes.
"""

import json
from typing import Dict, Any

from .base import BaseTool, ToolResult
from ..core.config import Config


class MemoryTool(BaseTool):
    """
    Tool for saving persistent memories.
    
    Allows the assistant to store important information that should persist
    across conversations, context truncations, and directory changes.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the memory tool.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self._memory_manager = None  # Will be injected by memory manager
    
    def set_memory_manager(self, memory_manager) -> None:
        """
        Set the memory manager instance.
        
        Args:
            memory_manager: Memory manager instance
        """
        self._memory_manager = memory_manager
    
    def get_name(self) -> str:
        """Get the tool name."""
        return "save_memory"
    
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute the save_memory tool.
        
        Args:
            args: Tool arguments containing:
                - content (str): Important information to remember
                - type (str): Memory type (user_preference, architectural_decision, 
                             important_fact, project_context)
                - scope (str, optional): Memory scope (directory, global), default: directory
        
        Returns:
            ToolResult with success/failure status
        """
        try:
            # Validate required arguments
            if "content" not in args:
                return ToolResult.fail("Missing required argument: content")
            
            if "type" not in args:
                return ToolResult.fail("Missing required argument: type")
            
            content = args["content"].strip()
            memory_type = args["type"].strip()
            scope = args.get("scope", "directory").strip()
            
            # Validate content
            if not content:
                return ToolResult.fail("Memory content cannot be empty")
            
            # Validate memory type
            valid_types = ["user_preference", "architectural_decision", "important_fact", "project_context"]
            if memory_type not in valid_types:
                return ToolResult.fail(f"Invalid memory type. Must be one of: {', '.join(valid_types)}")
            
            # Validate scope
            valid_scopes = ["directory", "global"]
            if scope not in valid_scopes:
                return ToolResult.fail(f"Invalid scope. Must be one of: {', '.join(valid_scopes)}")
            
            # Check if memory manager is available
            if self._memory_manager is None:
                return ToolResult.fail("Memory manager not available")
            
            # Save the memory
            memory_id = self._memory_manager.save_memory(content, memory_type, scope)
            
            # Format response based on scope
            scope_text = "globally" if scope == "global" else "for current directory"
            type_text = memory_type.replace("_", " ").title()
            
            result_message = f"✓ Saved {type_text} {scope_text}: {content}"
            
            # Add memory ID for potential future reference
            if memory_id:
                result_message += f" (ID: {memory_id})"
            
            return ToolResult.ok(result_message)
            
        except Exception as e:
            return ToolResult.fail(f"Failed to save memory: {str(e)}")
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get the tool definition for the AI model.
        
        Returns:
            Tool definition dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": "save_memory",
                "description": "Save important information that should persist across conversations and context truncations. Use this for user preferences, architectural decisions, important facts, and project context that you want to remember.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Important information to remember. Be concise but specific."
                        },
                        "type": {
                            "type": "string",
                            "enum": ["user_preference", "architectural_decision", "important_fact", "project_context"],
                            "description": "Type of memory: user_preference (user's preferred tools/patterns), architectural_decision (project structure/tech choices), important_fact (critical project info), project_context (specific constraints/requirements)"
                        },
                        "scope": {
                            "type": "string",
                            "enum": ["directory", "global"],
                            "default": "directory",
                            "description": "Memory scope: 'directory' for current project only, 'global' for all projects"
                        }
                    },
                    "required": ["content", "type"]
                }
            }
        }


class ListMemoriesTool(BaseTool):
    """
    Tool for listing stored memories (optional - can be used for debugging).
    """
    
    def __init__(self, config: Config):
        """
        Initialize the list memories tool.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self._memory_manager = None
    
    def set_memory_manager(self, memory_manager) -> None:
        """Set the memory manager instance."""
        self._memory_manager = memory_manager
    
    def get_name(self) -> str:
        """Get the tool name."""
        return "list_memories"
    
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute the list_memories tool.
        
        Args:
            args: Tool arguments containing:
                - scope (str, optional): Which memories to list (directory, global, all)
        
        Returns:
            ToolResult with memory list
        """
        try:
            if self._memory_manager is None:
                return ToolResult.fail("Memory manager not available")
            
            scope = args.get("scope", "all")
            
            # Get memories based on scope
            if scope == "directory":
                memories = self._memory_manager.get_directory_memories()
                title = "Directory Memories"
            elif scope == "global":
                memories = self._memory_manager.get_global_memories()
                title = "Global Memories"
            else:
                memories = self._memory_manager.get_all_memories()
                title = "All Memories"
            
            if not memories:
                return ToolResult.ok(f"No {scope} memories found")
            
            # Format memory list
            result_lines = [f"## {title}\n"]
            
            for memory in memories:
                memory_type = memory.get("type", "unknown").replace("_", " ").title()
                content = memory.get("content", "")
                memory_id = memory.get("id", "")
                created = memory.get("created", "")
                
                result_lines.append(f"**{memory_type}** ({memory_id}): {content}")
                if created:
                    result_lines.append(f"  _Created: {created}_")
                result_lines.append("")
            
            return ToolResult.ok("\n".join(result_lines))
            
        except Exception as e:
            return ToolResult.fail(f"Failed to list memories: {str(e)}")
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the tool definition for the AI model."""
        return {
            "type": "function",
            "function": {
                "name": "list_memories",
                "description": "List stored memories to see what information has been saved",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scope": {
                            "type": "string",
                            "enum": ["directory", "global", "all"],
                            "default": "all",
                            "description": "Which memories to list: directory (current project), global (all projects), all (both)"
                        }
                    },
                    "required": []
                }
            }
        }


class RemoveMemoryTool(BaseTool):
    """
    Tool for removing stored memories.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the remove memory tool.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self._memory_manager = None
    
    def set_memory_manager(self, memory_manager) -> None:
        """Set the memory manager instance."""
        self._memory_manager = memory_manager
    
    def get_name(self) -> str:
        """Get the tool name."""
        return "remove_memory"
    
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute the remove_memory tool.
        
        Args:
            args: Tool arguments containing:
                - memory_id (str): ID of the memory to remove
        
        Returns:
            ToolResult with success/failure status
        """
        try:
            if self._memory_manager is None:
                return ToolResult.fail("Memory manager not available")
            
            if "memory_id" not in args:
                return ToolResult.fail("Missing required argument: memory_id")
            
            memory_id = args["memory_id"].strip()
            
            if not memory_id:
                return ToolResult.fail("Memory ID cannot be empty")
            
            # Remove the memory
            success = self._memory_manager.remove_memory(memory_id)
            
            if success:
                return ToolResult.ok(f"✓ Removed memory: {memory_id}")
            else:
                return ToolResult.fail(f"Memory not found: {memory_id}")
            
        except Exception as e:
            return ToolResult.fail(f"Failed to remove memory: {str(e)}")
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Get the tool definition for the AI model."""
        return {
            "type": "function",
            "function": {
                "name": "remove_memory",
                "description": "Remove a stored memory by its ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory_id": {
                            "type": "string",
                            "description": "ID of the memory to remove"
                        }
                    },
                    "required": ["memory_id"]
                }
            }
        }