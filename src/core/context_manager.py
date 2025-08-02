#!/usr/bin/env python3

"""
Context Manager for Grok Assistant

Handles dual-mode context management with cache-optimized and smart truncation modes.
Provides turn-aware context truncation and memory integration.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from enum import Enum

from .config import Config
from .turn_logger import Turn, TurnLogger, TurnEvent
from ..utils.text_utils import estimate_token_usage, get_context_usage_info


class ContextMode(Enum):
    """Context management modes."""
    CACHE_OPTIMIZED = "cache_optimized"  # Append-only until truncation
    SMART_TRUNCATION = "smart_truncation"  # Immediate turn summarization


class ContextManager:
    """
    Manages conversation context with dual operating modes.
    
    Provides cache-friendly append-only mode and smart truncation mode
    with turn-aware context management and memory integration.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the context manager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.mode = ContextMode.SMART_TRUNCATION  # Default mode
        self.turn_logger = TurnLogger(config)
        
        # Context storage
        self.full_context: List[Dict[str, Any]] = []  # Full message history
        self.turn_logs: List[Turn] = []  # Summarized turn logs
        self.memories: List[Dict[str, Any]] = []  # Persistent memories
        
        # Token tracking
        self.cache_token_threshold = int(config.get_max_tokens_for_model(config.current_model) * 0.9)  # 90% for cache mode
        self.smart_truncation_threshold = int(config.get_max_tokens_for_model(config.current_model) * 0.7)  # 70% for smart mode
    
    def set_mode(self, mode: ContextMode) -> None:
        """
        Set the context management mode.
        
        Args:
            mode: Context management mode to use
        """
        old_mode = self.mode
        self.mode = mode
        
        # If switching from cache to smart mode, apply immediate truncation
        if old_mode == ContextMode.CACHE_OPTIMIZED and mode == ContextMode.SMART_TRUNCATION:
            self._apply_smart_truncation()
    
    def get_mode(self) -> ContextMode:
        """Get the current context management mode."""
        return self.mode
    
    def set_memories(self, memories: List[Dict[str, Any]]) -> None:
        """
        Set the persistent memories for context injection.
        
        Args:
            memories: List of memory objects to inject into context
        """
        self.memories = memories
    
    def add_system_message(self, content: str) -> None:
        """
        Add a system message to the context.
        
        Args:
            content: System message content
        """
        message = {"role": "system", "content": content}
        self.full_context.append(message)
    
    def start_turn(self, user_message: str) -> str:
        """
        Start a new conversation turn.
        
        Args:
            user_message: User message that starts the turn
            
        Returns:
            Turn ID for the new turn
        """
        # Check if we should truncate before starting new turn
        if self.mode == ContextMode.CACHE_OPTIMIZED:
            self._check_cache_truncation()
        
        # Start turn logging
        turn_id = self.turn_logger.start_turn(user_message)
        
        # Add user message to full context
        user_msg = {"role": "user", "content": user_message}
        self.full_context.append(user_msg)
        
        return turn_id
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Add an assistant message to the current turn.
        
        Args:
            content: Assistant message content
            tool_calls: Optional tool calls made by the assistant
        """
        # Log to turn logger
        self.turn_logger.add_assistant_message(content)
        
        # Add to full context
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.full_context.append(message)
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any]) -> None:
        """
        Add a tool call to the current turn.
        
        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
        """
        self.turn_logger.add_tool_call(tool_name, args)
    
    def add_tool_response(self, tool_name: str, result: str) -> None:
        """
        Add a tool response to the current turn.
        
        Args:
            tool_name: Name of the tool
            result: Tool execution result
        """
        # Log to turn logger
        self.turn_logger.add_tool_response(tool_name, result)
        
        # Add to full context
        message = {"role": "tool", "content": result}
        self.full_context.append(message)
    
    def complete_turn(self, summary: Optional[str] = None) -> Optional[Turn]:
        """
        Complete the current turn and apply truncation if needed.
        
        Args:
            summary: Optional summary of what was accomplished
            
        Returns:
            The completed turn if one was active
        """
        if not self.turn_logger.is_turn_active():
            return None
        
        # Complete the turn
        completed_turn = self.turn_logger.complete_turn(summary)
        
        # Apply mode-specific context management
        if self.mode == ContextMode.SMART_TRUNCATION:
            # Immediately convert turn to log and truncate
            self.turn_logs.append(completed_turn)
            self._apply_smart_truncation()
        else:
            # Cache mode: just store the turn log for potential future truncation
            self.turn_logs.append(completed_turn)
        
        return completed_turn
    
    def get_context_for_api(self) -> List[Dict[str, Any]]:
        """
        Get the current context formatted for API calls.
        
        Returns:
            List of messages ready for API consumption
        """
        context = []
        
        # Add system prompt (always first)
        system_prompt = self._build_system_prompt()
        context.append({"role": "system", "content": system_prompt})
        
        # Add context based on mode
        if self.mode == ContextMode.SMART_TRUNCATION and self.turn_logs:
            # Use turn logs for older context
            context.extend(self._build_context_from_turn_logs())
        
        # Add recent full context
        context.extend(self._get_recent_full_context())
        
        return context
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with memories included."""
        # Get base system prompt
        base_prompt = self.config.get_system_prompt()
        
        # Add memories if any exist
        if self.memories:
            memory_section = "\n\n## Persistent Memories\n\n"
            for memory in self.memories:
                memory_type = memory.get("type", "note")
                content = memory.get("content", "")
                memory_section += f"- **{memory_type.replace('_', ' ').title()}**: {content}\n"
            
            return base_prompt + memory_section
        
        return base_prompt
    
    def _build_context_from_turn_logs(self) -> List[Dict[str, Any]]:
        """Build context messages from turn logs."""
        context = []
        
        # Add turn summaries as system messages
        for turn_log in self.turn_logs[:-3]:  # All but last 3 turns
            summary_msg = {
                "role": "system",
                "content": f"Previous turn summary: {turn_log.summary}"
            }
            context.append(summary_msg)
        
        # Add last few turns in full detail
        for turn_log in self.turn_logs[-3:]:
            context.extend(self._turn_to_messages(turn_log))
        
        return context
    
    def _turn_to_messages(self, turn: Turn) -> List[Dict[str, Any]]:
        """Convert a turn log back to message format."""
        messages = []
        
        for event in turn.events:
            if event.type == "user_message":
                messages.append({"role": "user", "content": event.content})
            elif event.type == "assistant_message":
                messages.append({"role": "assistant", "content": event.content})
            elif event.type == "tool_response":
                messages.append({"role": "tool", "content": event.result})
        
        return messages
    
    def _get_recent_full_context(self) -> List[Dict[str, Any]]:
        """Get recent full context messages."""
        if self.mode == ContextMode.SMART_TRUNCATION:
            # Return messages from current turn only
            if self.turn_logger.is_turn_active():
                return self.turn_logger.get_turn_events_as_messages()
            else:
                return []
        else:
            # Cache mode: return all full context
            return self.full_context[1:]  # Skip system prompt (added separately)
    
    def _check_cache_truncation(self) -> None:
        """Check if cache mode needs truncation and apply if necessary."""
        if self.mode != ContextMode.CACHE_OPTIMIZED:
            return
        
        # Estimate tokens for current context
        estimated_tokens, _ = estimate_token_usage(self.full_context)
        
        if estimated_tokens > self.cache_token_threshold:
            self._apply_cache_truncation()
    
    def _apply_cache_truncation(self) -> None:
        """Apply truncation for cache-optimized mode."""
        # Convert context to turn logs and apply smart truncation
        self._convert_full_context_to_turns()
        self._apply_smart_truncation()
        
        # Clear full context (will be rebuilt from turn logs)
        self.full_context = []
    
    def _apply_smart_truncation(self) -> None:
        """Apply smart truncation keeping only essential turn logs."""
        if len(self.turn_logs) <= 3:
            return  # Keep at least 3 turns
        
        # Calculate target token count (leave room for response)
        max_tokens = self.config.get_max_tokens_for_model(self.config.current_model)
        target_tokens = int(max_tokens * 0.6)  # Use 60% of context for history
        
        # Get current context and estimate tokens
        current_context = self.get_context_for_api()
        estimated_tokens, _ = estimate_token_usage(current_context)
        
        # If we're under the target, no need to truncate
        if estimated_tokens <= target_tokens:
            return
        
        # Keep recent turns and compress older ones
        # Strategy: Keep last 3 turns in full detail, summarize the rest
        if len(self.turn_logs) > 5:
            # Keep first turn (often contains important setup)
            # Compress middle turns (keep every other turn summary)
            # Keep last 3 turns in full detail
            
            preserved_turns = []
            
            # Always keep first turn if it's important
            if self.turn_logs:
                preserved_turns.append(self.turn_logs[0])
            
            # For middle turns, keep every 2nd turn summary
            middle_turns = self.turn_logs[1:-3]
            for i in range(0, len(middle_turns), 2):
                turn = middle_turns[i]
                # Create a compressed version with just summary
                compressed_turn = Turn(
                    turn_id=f"{turn.turn_id}_compressed",
                    start_time=turn.start_time,
                    events=[],  # Remove detailed events
                    end_time=turn.end_time,
                    files_modified=turn.files_modified,
                    files_created=turn.files_created,
                    files_read=turn.files_read,
                    tools_used=turn.tools_used,
                    summary=turn.summary
                )
                preserved_turns.append(compressed_turn)
            
            # Always keep last 3 turns in full detail
            preserved_turns.extend(self.turn_logs[-3:])
            
            self.turn_logs = preserved_turns
    
    def _convert_full_context_to_turns(self) -> None:
        """Convert full context to turn logs."""
        if not self.full_context:
            return
        
        # Group messages into turns based on user messages
        current_turn_events = []
        turn_counter = len(self.turn_logs) + 1
        
        i = 0
        while i < len(self.full_context):
            message = self.full_context[i]
            role = message.get("role")
            content = message.get("content", "")
            
            if role == "system":
                # Skip system messages in turn conversion
                i += 1
                continue
            elif role == "user":
                # Start of a new turn
                if current_turn_events:
                    # Complete previous turn
                    self._create_turn_from_events(current_turn_events, turn_counter)
                    turn_counter += 1
                
                # Start new turn
                current_turn_events = [TurnEvent(type="user_message", content=content)]
            elif role == "assistant":
                current_turn_events.append(TurnEvent(type="assistant_message", content=content))
            elif role == "tool":
                # Try to determine tool name from context or use generic
                tool_name = "unknown_tool"
                current_turn_events.append(TurnEvent(type="tool_response", tool=tool_name, result=content))
            
            i += 1
        
        # Complete the last turn if there are events
        if current_turn_events:
            self._create_turn_from_events(current_turn_events, turn_counter)
    
    def _create_turn_from_events(self, events: List, turn_counter: int) -> None:
        """Create a turn from a list of events."""
        from datetime import datetime
        
        turn = Turn(
            turn_id=f"turn_{turn_counter:03d}",
            start_time=datetime.now().isoformat(),
            events=events,
            end_time=datetime.now().isoformat(),
            summary=self._generate_turn_summary_from_events(events)
        )
        
        self.turn_logs.append(turn)
    
    def _generate_turn_summary_from_events(self, events: List) -> str:
        """Generate a summary from turn events."""
        user_msgs = [e for e in events if e.type == "user_message"]
        assistant_msgs = [e for e in events if e.type == "assistant_message"]
        tool_calls = [e for e in events if e.type == "tool_call"]
        
        summary_parts = []
        
        if user_msgs:
            user_content = user_msgs[0].content[:50] + "..." if len(user_msgs[0].content) > 50 else user_msgs[0].content
            summary_parts.append(f"User: {user_content}")
        
        if tool_calls:
            tools = list(set(e.tool for e in tool_calls if e.tool))
            summary_parts.append(f"Tools: {', '.join(tools)}")
        
        if assistant_msgs:
            summary_parts.append(f"Assistant responded ({len(assistant_msgs)} messages)")
        
        return "; ".join(summary_parts) if summary_parts else "Turn completed"
    
    def get_context_stats(self) -> Dict[str, Any]:
        """
        Get context usage statistics.
        
        Returns:
            Dictionary with context usage information
        """
        current_context = self.get_context_for_api()
        context_info = get_context_usage_info(current_context, self.config.current_model, self.config)
        
        stats = {
            **context_info,
            "mode": self.mode.value,
            "turn_logs_count": len(self.turn_logs),
            "full_context_messages": len(self.full_context),
            "memories_count": len(self.memories),
            "active_turn": self.turn_logger.is_turn_active()
        }
        
        return stats
    
    def clear_context(self, keep_memories: bool = True) -> None:
        """
        Clear all context data.
        
        Args:
            keep_memories: Whether to keep persistent memories
        """
        self.full_context = []
        self.turn_logs = []
        
        if not keep_memories:
            self.memories = []
        
        # Reset turn logger
        if self.turn_logger.is_turn_active():
            self.turn_logger.complete_turn("Context cleared")
    
    def export_context(self, include_full_context: bool = False) -> Dict[str, Any]:
        """
        Export context data for debugging or analysis.
        
        Args:
            include_full_context: Whether to include full message history
            
        Returns:
            Dictionary containing context data
        """
        export_data = {
            "mode": self.mode.value,
            "memories": self.memories,
            "turn_logs": [turn.to_dict() for turn in self.turn_logs],
            "stats": self.get_context_stats()
        }
        
        if include_full_context:
            export_data["full_context"] = self.full_context
        
        return export_data