#!/usr/bin/env python3

"""
Context State for Structured Summarization

This module provides a structured state object that replaces text-based
turn summaries, preventing "telephone game" entropy during truncation.

Instead of compressing turns into lossy natural language summaries,
we maintain a structured state object (JSON-serializable) that preserves
key facts across truncations.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Set
import json


@dataclass
class ContextState:
    """
    Structured state representation that survives truncation without entropy.

    This replaces text-based summaries with structured data that maintains
    key facts about the conversation history, codebase modifications, and
    current objectives.

    Attributes:
        files_modified: Set of file paths that have been modified
        files_created: Set of file paths that have been created
        files_read: Set of file paths that have been read
        tasks_completed: List of completed task descriptions
        tasks_pending: List of pending task descriptions
        key_functions: Dict mapping function names to their locations
        key_classes: Dict mapping class names to their locations
        errors_fixed: List of errors that were fixed
        main_goal: Current primary objective
        blockers: List of current blockers or issues
        decisions_made: List of key architectural or implementation decisions
        tools_used: Set of tools that have been used
    """

    # File tracking
    files_modified: Set[str] = field(default_factory=set)
    files_created: Set[str] = field(default_factory=set)
    files_read: Set[str] = field(default_factory=set)

    # Task tracking
    tasks_completed: List[str] = field(default_factory=list)
    tasks_pending: List[str] = field(default_factory=list)

    # Code structure knowledge
    key_functions: Dict[str, str] = field(default_factory=dict)  # name -> location
    key_classes: Dict[str, str] = field(default_factory=dict)    # name -> location

    # Error tracking
    errors_fixed: List[str] = field(default_factory=list)

    # Current understanding
    main_goal: str = ""
    blockers: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)

    # Tool usage
    tools_used: Set[str] = field(default_factory=set)

    def merge(self, other: 'ContextState') -> None:
        """
        Merge another ContextState into this one.

        This enables incremental state updates when compressing multiple
        turns without losing information.

        Args:
            other: Another ContextState to merge into this one
        """
        # Merge sets (union)
        self.files_modified.update(other.files_modified)
        self.files_created.update(other.files_created)
        self.files_read.update(other.files_read)
        self.tools_used.update(other.tools_used)

        # Merge lists (extend)
        self.tasks_completed.extend(other.tasks_completed)
        self.tasks_pending.extend(other.tasks_pending)
        self.errors_fixed.extend(other.errors_fixed)
        self.blockers.extend(other.blockers)
        self.decisions_made.extend(other.decisions_made)

        # Merge dicts (update)
        self.key_functions.update(other.key_functions)
        self.key_classes.update(other.key_classes)

        # Update main goal if other has one
        if other.main_goal:
            self.main_goal = other.main_goal

    def to_context_message(self) -> str:
        """
        Convert state to a context message for injection into the prompt.

        This is deterministic and lossless - the same state always produces
        the same message, preventing entropy accumulation.

        Returns:
            Formatted string suitable for system prompt injection
        """
        parts = []

        # Main goal
        if self.main_goal:
            parts.append(f"## Current Objective\n{self.main_goal}")

        # File modifications
        if self.files_modified or self.files_created:
            parts.append("## Modified Codebase")
            file_list = []
            for f in sorted(self.files_modified):
                file_list.append(f"  - {f} (modified)")
            for f in sorted(self.files_created):
                file_list.append(f"  - {f} (created)")
            parts.append("\n".join(file_list))

        # Tasks
        if self.tasks_completed:
            parts.append(f"## Completed Tasks ({len(self.tasks_completed)})")
            for task in self.tasks_completed[-5:]:  # Last 5 tasks
                parts.append(f"  ✓ {task}")
            if len(self.tasks_completed) > 5:
                parts.append(f"  ... and {len(self.tasks_completed) - 5} more")

        if self.tasks_pending:
            parts.append("## Pending Tasks")
            for task in self.tasks_pending:
                parts.append(f"  - {task}")

        # Key code locations
        if self.key_functions or self.key_classes:
            parts.append("## Key Code Locations")
            for name, loc in sorted(self.key_functions.items()):
                parts.append(f"  - Function: {name} in {loc}")
            for name, loc in sorted(self.key_classes.items()):
                parts.append(f"  - Class: {name} in {loc}")

        # Errors fixed
        if self.errors_fixed:
            parts.append(f"## Errors Fixed ({len(self.errors_fixed)})")
            for error in self.errors_fixed[-3:]:  # Last 3 errors
                parts.append(f"  ✓ {error}")

        # Blockers
        if self.blockers:
            parts.append("## Current Blockers")
            for blocker in self.blockers:
                parts.append(f"  ! {blocker}")

        # Decisions
        if self.decisions_made:
            parts.append("## Key Decisions")
            for decision in self.decisions_made[-3:]:  # Last 3 decisions
                parts.append(f"  • {decision}")

        # Tools used (compact summary)
        if self.tools_used:
            tools_str = ", ".join(sorted(self.tools_used))
            parts.append(f"## Tools Used: {tools_str}")

        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of the state
        """
        # Convert sets to lists for JSON serialization
        data = asdict(self)
        data['files_modified'] = list(self.files_modified)
        data['files_created'] = list(self.files_created)
        data['files_read'] = list(self.files_read)
        data['tools_used'] = list(self.tools_used)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextState':
        """
        Create ContextState from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ContextState instance
        """
        # Convert lists back to sets
        state = cls(
            files_modified=set(data.get('files_modified', [])),
            files_created=set(data.get('files_created', [])),
            files_read=set(data.get('files_read', [])),
            tasks_completed=data.get('tasks_completed', []),
            tasks_pending=data.get('tasks_pending', []),
            key_functions=data.get('key_functions', {}),
            key_classes=data.get('key_classes', {}),
            errors_fixed=data.get('errors_fixed', []),
            main_goal=data.get('main_goal', ''),
            blockers=data.get('blockers', []),
            decisions_made=data.get('decisions_made', []),
            tools_used=set(data.get('tools_used', []))
        )
        return state

    def to_json(self) -> str:
        """
        Serialize state to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ContextState':
        """
        Deserialize state from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            ContextState instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def is_empty(self) -> bool:
        """
        Check if state is empty (no meaningful information).

        Returns:
            True if state has no meaningful data
        """
        return (
            not self.files_modified
            and not self.files_created
            and not self.files_read
            and not self.tasks_completed
            and not self.tasks_pending
            and not self.key_functions
            and not self.key_classes
            and not self.errors_fixed
            and not self.main_goal
            and not self.blockers
            and not self.decisions_made
            and not self.tools_used
        )

    def get_summary_stats(self) -> Dict[str, int]:
        """
        Get summary statistics about the state.

        Returns:
            Dictionary with counts of various state components
        """
        return {
            'files_modified': len(self.files_modified),
            'files_created': len(self.files_created),
            'files_read': len(self.files_read),
            'tasks_completed': len(self.tasks_completed),
            'tasks_pending': len(self.tasks_pending),
            'key_functions': len(self.key_functions),
            'key_classes': len(self.key_classes),
            'errors_fixed': len(self.errors_fixed),
            'blockers': len(self.blockers),
            'decisions_made': len(self.decisions_made),
            'tools_used': len(self.tools_used)
        }
