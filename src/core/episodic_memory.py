#!/usr/bin/env python3

"""
Episodic Memory System for Agentic Reasoning

Implements hierarchical, trajectory-based memory storage that captures
full task episodes with planning, execution, and reflection phases.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..utils.logging_config import get_logger
from .config import Config


class Episode:
    """
    Represents a complete task episode with planning, actions, and outcomes.
    """

    def __init__(self, episode_id: str, goal: str):
        """
        Initialize an episode.

        Args:
            episode_id: Unique episode identifier
            goal: The high-level goal for this episode
        """
        self.episode_id = episode_id
        self.goal = goal
        self.created = datetime.now().isoformat()
        self.completed = None
        self.plan = None
        self.actions = []
        self.reflections = []
        self.outcome = None
        self.success = None

    def set_plan(self, plan: dict) -> None:
        """Set the plan for this episode."""
        self.plan = plan

    def add_action(self, action_type: str, description: str, result: str, success: bool) -> None:
        """
        Add an action to this episode.

        Args:
            action_type: Type of action (tool_call, thought, etc.)
            description: Description of the action
            result: Result or observation
            success: Whether action succeeded
        """
        self.actions.append({
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "description": description,
            "result": result,
            "success": success
        })

    def add_reflection(self, reflection: str) -> None:
        """
        Add a reflection to this episode.

        Args:
            reflection: Reflection text
        """
        self.reflections.append({
            "timestamp": datetime.now().isoformat(),
            "content": reflection
        })

    def complete(self, outcome: str, success: bool) -> None:
        """
        Mark episode as complete.

        Args:
            outcome: Final outcome description
            success: Whether the episode succeeded
        """
        self.completed = datetime.now().isoformat()
        self.outcome = outcome
        self.success = success

    def to_dict(self) -> dict:
        """Convert episode to dictionary."""
        return {
            "episode_id": self.episode_id,
            "goal": self.goal,
            "created": self.created,
            "completed": self.completed,
            "plan": self.plan,
            "actions": self.actions,
            "reflections": self.reflections,
            "outcome": self.outcome,
            "success": self.success
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Episode':
        """Create episode from dictionary."""
        episode = cls(data["episode_id"], data["goal"])
        episode.created = data.get("created")
        episode.completed = data.get("completed")
        episode.plan = data.get("plan")
        episode.actions = data.get("actions", [])
        episode.reflections = data.get("reflections", [])
        episode.outcome = data.get("outcome")
        episode.success = data.get("success")
        return episode

    def get_summary(self) -> str:
        """Generate a summary of this episode."""
        status = "✓ Success" if self.success else "✗ Failed" if self.success is False else "⧗ In Progress"
        action_count = len(self.actions)
        reflection_count = len(self.reflections)

        summary = f"{status} | {self.goal} | {action_count} actions, {reflection_count} reflections"

        if self.outcome:
            summary += f" | Outcome: {self.outcome[:100]}"

        return summary


class EpisodicMemoryManager:
    """
    Manages episodic memories with trajectory storage and summarization.

    Extends the basic memory system with full episode tracking including
    plans, action sequences, reflections, and outcomes.
    """

    def __init__(self, config: Config):
        """
        Initialize episodic memory manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = get_logger("episodic_memory")
        self.current_directory = config.base_dir

        # Episode storage
        self.global_episodes: list[Episode] = []
        self.directory_episodes: dict[str, list[Episode]] = {}

        # Current active episode
        self.current_episode: Optional[Episode] = None

        # File paths
        self.global_episodes_file = Path.home() / ".grok_global_episodes.json"

        # Load episodes
        self._load_global_episodes()
        self._load_directory_episodes(self.current_directory)

        self.logger.info(
            f"EpisodicMemoryManager initialized: {len(self.global_episodes)} global episodes"
        )

    def start_episode(self, goal: str, scope: str = "directory") -> str:
        """
        Start a new episode.

        Args:
            goal: The goal for this episode
            scope: Scope (directory or global)

        Returns:
            Episode ID
        """
        episode_id = f"ep_{uuid.uuid4().hex[:8]}"
        episode = Episode(episode_id, goal)

        self.current_episode = episode

        # Store reference by scope
        if scope == "global":
            self.global_episodes.append(episode)
        else:
            dir_str = str(self.current_directory)
            if dir_str not in self.directory_episodes:
                self.directory_episodes[dir_str] = []
            self.directory_episodes[dir_str].append(episode)

        self.logger.info(f"Started episode {episode_id}: {goal}")
        return episode_id

    def add_plan_to_current_episode(self, plan: dict) -> None:
        """Add plan to current episode."""
        if self.current_episode:
            self.current_episode.set_plan(plan)
            self._save_episodes()

    def add_action_to_current_episode(
        self, action_type: str, description: str, result: str, success: bool
    ) -> None:
        """Add action to current episode."""
        if self.current_episode:
            self.current_episode.add_action(action_type, description, result, success)
            self._save_episodes()

    def add_reflection_to_current_episode(self, reflection: str) -> None:
        """Add reflection to current episode."""
        if self.current_episode:
            self.current_episode.add_reflection(reflection)
            self._save_episodes()

    def complete_current_episode(self, outcome: str, success: bool) -> Optional[str]:
        """
        Complete the current episode.

        Args:
            outcome: Final outcome description
            success: Whether the episode succeeded

        Returns:
            Episode ID if episode was active, None otherwise
        """
        if self.current_episode:
            self.current_episode.complete(outcome, success)
            episode_id = self.current_episode.episode_id
            self.current_episode = None
            self._save_episodes()
            self.logger.info(f"Completed episode {episode_id}")
            return episode_id
        return None

    def get_episodes(
        self, scope: Optional[str] = None, limit: int = 10, successful_only: bool = False
    ) -> list[Episode]:
        """
        Get episodes.

        Args:
            scope: Filter by scope (global, directory, or None for all)
            limit: Maximum number of episodes to return
            successful_only: Only return successful episodes

        Returns:
            List of episodes
        """
        episodes = []

        if scope is None or scope == "global":
            episodes.extend(self.global_episodes)

        if scope is None or scope == "directory":
            dir_str = str(self.current_directory)
            episodes.extend(self.directory_episodes.get(dir_str, []))

        # Filter by success if requested
        if successful_only:
            episodes = [ep for ep in episodes if ep.success]

        # Sort by creation time (newest first)
        episodes.sort(key=lambda ep: ep.created, reverse=True)

        return episodes[:limit]

    def get_relevant_episodes(self, query: str, limit: int = 3) -> list[Episode]:
        """
        Get episodes relevant to a query.

        Uses simple keyword matching for now. Can be enhanced with
        embeddings/semantic search later.

        Args:
            query: Query string
            limit: Maximum number of episodes to return

        Returns:
            List of relevant episodes
        """
        all_episodes = self.get_episodes()
        query_lower = query.lower()

        # Score episodes by keyword match
        scored_episodes = []
        for episode in all_episodes:
            score = 0

            # Check goal
            if query_lower in episode.goal.lower():
                score += 3

            # Check outcome
            if episode.outcome and query_lower in episode.outcome.lower():
                score += 2

            # Check actions
            for action in episode.actions:
                if query_lower in action.get("description", "").lower():
                    score += 1

            if score > 0:
                scored_episodes.append((score, episode))

        # Sort by score
        scored_episodes.sort(key=lambda x: x[0], reverse=True)

        return [ep for _, ep in scored_episodes[:limit]]

    def summarize_episodes(self, max_size_kb: int = 10) -> dict[str, Any]:
        """
        Summarize old episodes to save space.

        Args:
            max_size_kb: Maximum size in KB before triggering summarization

        Returns:
            Summary statistics
        """
        # Check size of episode files
        global_size = (
            self.global_episodes_file.stat().st_size / 1024
            if self.global_episodes_file.exists()
            else 0
        )

        if global_size < max_size_kb:
            return {"summarized": False, "reason": "Below size threshold"}

        # Summarize old episodes (keep only key insights)
        summarized_count = 0
        for episode in self.global_episodes:
            if episode.completed and len(episode.actions) > 5:
                # Keep only summary, not full action list
                episode.actions = [
                    {
                        "type": "summary",
                        "description": f"Episode had {len(episode.actions)} actions",
                        "result": "Summarized to save space",
                        "success": episode.success
                    }
                ]
                summarized_count += 1

        self._save_episodes()

        return {
            "summarized": True,
            "episodes_summarized": summarized_count,
            "size_before_kb": global_size
        }

    def change_directory(self, new_directory: Path) -> dict[str, Any]:
        """
        Change directory and load corresponding episodes.

        Args:
            new_directory: New directory path

        Returns:
            Information about the directory change
        """
        old_directory = self.current_directory
        self.current_directory = new_directory

        # Load episodes for new directory
        self._load_directory_episodes(new_directory)

        new_dir_str = str(new_directory)
        episode_count = len(self.directory_episodes.get(new_dir_str, []))

        return {
            "old_directory": str(old_directory),
            "new_directory": str(new_directory),
            "episode_count": episode_count
        }

    def get_episodes_for_context(self, limit: int = 3) -> list[dict]:
        """
        Get episodes formatted for context injection.

        Returns:
            List of episode summaries for context
        """
        recent_episodes = self.get_episodes(limit=limit, successful_only=True)

        return [
            {
                "episode_id": ep.episode_id,
                "goal": ep.goal,
                "summary": ep.get_summary(),
                "outcome": ep.outcome
            }
            for ep in recent_episodes
        ]

    def _load_global_episodes(self) -> None:
        """Load global episodes from file."""
        try:
            if self.global_episodes_file.exists():
                with open(self.global_episodes_file, encoding="utf-8") as f:
                    data = json.load(f)
                    episodes_data = data.get("episodes", [])
                    self.global_episodes = [
                        Episode.from_dict(ep_data) for ep_data in episodes_data
                    ]
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            self.logger.warning(f"Could not load global episodes: {e}")
            self.global_episodes = []

    def _load_directory_episodes(self, directory: Path) -> None:
        """Load episodes for a specific directory."""
        dir_str = str(directory)
        episodes_file = directory / ".grok_episodes.json"

        try:
            if episodes_file.exists():
                with open(episodes_file, encoding="utf-8") as f:
                    data = json.load(f)
                    episodes_data = data.get("episodes", [])
                    self.directory_episodes[dir_str] = [
                        Episode.from_dict(ep_data) for ep_data in episodes_data
                    ]
            else:
                self.directory_episodes[dir_str] = []
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            self.logger.warning(f"Could not load directory episodes: {e}")
            self.directory_episodes[dir_str] = []

    def _save_episodes(self) -> None:
        """Save all episodes to files."""
        self._save_global_episodes()
        self._save_directory_episodes(self.current_directory)

    def _save_global_episodes(self) -> None:
        """Save global episodes to file."""
        try:
            self.global_episodes_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "episodes": [ep.to_dict() for ep in self.global_episodes],
                "last_updated": datetime.now().isoformat()
            }

            with open(self.global_episodes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            self.logger.error(f"Could not save global episodes: {e}")

    def _save_directory_episodes(self, directory: Path) -> None:
        """Save episodes for a specific directory."""
        dir_str = str(directory)
        episodes_file = directory / ".grok_episodes.json"

        try:
            episodes = self.directory_episodes.get(dir_str, [])

            data = {
                "directory": dir_str,
                "episodes": [ep.to_dict() for ep in episodes],
                "last_updated": datetime.now().isoformat()
            }

            with open(episodes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            self.logger.error(f"Could not save directory episodes: {e}")

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about episodes."""
        all_episodes = self.get_episodes(limit=1000)
        completed = [ep for ep in all_episodes if ep.completed]
        successful = [ep for ep in all_episodes if ep.success]

        return {
            "total_episodes": len(all_episodes),
            "global_episodes": len(self.global_episodes),
            "directory_episodes": len(self.directory_episodes.get(str(self.current_directory), [])),
            "completed_episodes": len(completed),
            "successful_episodes": len(successful),
            "active_episode": self.current_episode.episode_id if self.current_episode else None,
            "success_rate": len(successful) / len(completed) if completed else 0.0
        }
