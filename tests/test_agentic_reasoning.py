#!/usr/bin/env python3

"""
Tests for agentic reasoning features

Tests for planning, reflection, episodic memory, and multi-agent coordination.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.core.config import Config
from src.core.episodic_memory import Episode, EpisodicMemoryManager
from src.tools.planning_tool import GeneratePlanTool, ReflectTool
from src.tools.multiagent_tool import BlackboardCommunication
from src.commands.agentic_commands import PlanCommand, ImproveCommand, SpawnCommand, EpisodesCommand


class TestEpisodicMemory:
    """Test episodic memory functionality."""

    def test_episode_creation(self):
        """Test creating a new episode."""
        episode = Episode("ep_test123", "Test goal")

        assert episode.episode_id == "ep_test123"
        assert episode.goal == "Test goal"
        assert episode.plan is None
        assert len(episode.actions) == 0
        assert len(episode.reflections) == 0
        assert episode.success is None

    def test_episode_plan_setting(self):
        """Test setting a plan for an episode."""
        episode = Episode("ep_test123", "Test goal")
        plan = {
            "goal": "Test goal",
            "steps": [
                {"step_number": 1, "action": "Step 1"},
                {"step_number": 2, "action": "Step 2"}
            ]
        }

        episode.set_plan(plan)
        assert episode.plan == plan
        assert len(episode.plan["steps"]) == 2

    def test_episode_add_action(self):
        """Test adding actions to an episode."""
        episode = Episode("ep_test123", "Test goal")

        episode.add_action("tool_call", "Read file", "Success", True)
        episode.add_action("tool_call", "Write file", "Error: Permission denied", False)

        assert len(episode.actions) == 2
        assert episode.actions[0]["type"] == "tool_call"
        assert episode.actions[0]["success"] is True
        assert episode.actions[1]["success"] is False

    def test_episode_add_reflection(self):
        """Test adding reflections to an episode."""
        episode = Episode("ep_test123", "Test goal")

        episode.add_reflection("The file write failed due to permissions")
        episode.add_reflection("Should check permissions before writing")

        assert len(episode.reflections) == 2
        assert "permissions" in episode.reflections[0]["content"]

    def test_episode_completion(self):
        """Test completing an episode."""
        episode = Episode("ep_test123", "Test goal")

        episode.complete("Task completed successfully", True)

        assert episode.completed is not None
        assert episode.outcome == "Task completed successfully"
        assert episode.success is True

    def test_episode_serialization(self):
        """Test episode to/from dict conversion."""
        episode = Episode("ep_test123", "Test goal")
        episode.set_plan({"goal": "Test goal", "steps": []})
        episode.add_action("tool_call", "Test action", "Success", True)
        episode.complete("Done", True)

        # Convert to dict
        episode_dict = episode.to_dict()

        assert episode_dict["episode_id"] == "ep_test123"
        assert episode_dict["goal"] == "Test goal"
        assert len(episode_dict["actions"]) == 1
        assert episode_dict["success"] is True

        # Convert back from dict
        restored_episode = Episode.from_dict(episode_dict)

        assert restored_episode.episode_id == episode.episode_id
        assert restored_episode.goal == episode.goal
        assert len(restored_episode.actions) == len(episode.actions)

    def test_episodic_memory_manager(self, tmp_path):
        """Test episodic memory manager."""
        # Create config with temp directory
        config = Config()
        config.base_dir = tmp_path

        manager = EpisodicMemoryManager(config)

        # Start an episode
        episode_id = manager.start_episode("Test goal", scope="directory")
        assert episode_id.startswith("ep_")
        assert manager.current_episode is not None

        # Add plan
        plan = {"goal": "Test goal", "steps": []}
        manager.add_plan_to_current_episode(plan)
        assert manager.current_episode.plan == plan

        # Add action
        manager.add_action_to_current_episode("tool_call", "Test", "Success", True)
        assert len(manager.current_episode.actions) == 1

        # Add reflection
        manager.add_reflection_to_current_episode("Good work")
        assert len(manager.current_episode.reflections) == 1

        # Complete episode
        completed_id = manager.complete_current_episode("Finished", True)
        assert completed_id == episode_id
        assert manager.current_episode is None

        # Get episodes
        episodes = manager.get_episodes(limit=10)
        assert len(episodes) == 1
        assert episodes[0].episode_id == episode_id

    def test_episode_retrieval(self, tmp_path):
        """Test retrieving relevant episodes."""
        config = Config()
        config.base_dir = tmp_path

        manager = EpisodicMemoryManager(config)

        # Create multiple episodes
        manager.start_episode("Fix authentication bug", scope="directory")
        manager.complete_current_episode("Fixed authentication", True)

        manager.start_episode("Add user registration", scope="directory")
        manager.complete_current_episode("Added registration", True)

        manager.start_episode("Update database schema", scope="directory")
        manager.complete_current_episode("Updated schema", True)

        # Retrieve relevant episodes
        auth_episodes = manager.get_relevant_episodes("authentication", limit=2)
        assert len(auth_episodes) >= 1
        assert any("authentication" in ep.goal.lower() for ep in auth_episodes)

    def test_episode_statistics(self, tmp_path):
        """Test episode statistics."""
        config = Config()
        config.base_dir = tmp_path

        manager = EpisodicMemoryManager(config)

        # Create successful and failed episodes
        manager.start_episode("Task 1", scope="directory")
        manager.complete_current_episode("Success", True)

        manager.start_episode("Task 2", scope="directory")
        manager.complete_current_episode("Failed", False)

        manager.start_episode("Task 3", scope="directory")
        manager.complete_current_episode("Success", True)

        # Get statistics
        stats = manager.get_statistics()

        assert stats["total_episodes"] == 3
        assert stats["completed_episodes"] == 3
        assert stats["successful_episodes"] == 2
        assert stats["success_rate"] == pytest.approx(2/3)


class TestPlanningTool:
    """Test planning tool functionality."""

    def test_generate_plan_tool_basic(self, tmp_path):
        """Test basic plan generation."""
        config = Config()
        config.base_dir = tmp_path

        tool = GeneratePlanTool(config)

        assert tool.name == "generate_plan"
        assert "plan" in tool.description.lower()

        # Test without client (should use simple plan)
        result = tool.execute(goal="Refactor authentication module", max_steps=5)

        assert result.success
        assert "plan" in result.result.lower()

    def test_generate_plan_parameters(self, tmp_path):
        """Test plan generation with parameters."""
        config = Config()
        config.base_dir = tmp_path

        tool = GeneratePlanTool(config)

        # Test with context
        result = tool.execute(
            goal="Add OAuth2 support",
            context="Currently using basic auth",
            max_steps=3
        )

        assert result.success


class TestReflectionTool:
    """Test reflection tool functionality."""

    def test_reflect_tool_basic(self, tmp_path):
        """Test basic reflection."""
        config = Config()
        config.base_dir = tmp_path

        tool = ReflectTool(config)

        assert tool.name == "reflect"
        assert "reflect" in tool.description.lower()

        # Test reflection on failure
        result = tool.execute(
            action="write_file",
            outcome="Permission denied",
            expected="File written successfully",
            error="PermissionError: Access denied"
        )

        assert result.success
        assert "reflect" in result.result.lower() or "analysis" in result.result.lower()

    def test_reflect_on_success(self, tmp_path):
        """Test reflection on successful action."""
        config = Config()
        config.base_dir = tmp_path

        tool = ReflectTool(config)

        result = tool.execute(
            action="run_tests",
            outcome="All tests passed"
        )

        assert result.success


class TestMultiAgentTools:
    """Test multi-agent coordination tools."""

    def test_blackboard_communication(self, tmp_path):
        """Test blackboard communication."""
        blackboard_path = tmp_path / "blackboard.json"
        blackboard = BlackboardCommunication(blackboard_path)

        # Post message
        blackboard.post_message("agent_1", "Hello from agent 1", "info")

        # Get messages
        messages = blackboard.get_messages()
        assert len(messages) == 1
        assert messages[0]["agent_id"] == "agent_1"
        assert messages[0]["content"] == "Hello from agent 1"

    def test_blackboard_message_filtering(self, tmp_path):
        """Test blackboard message filtering."""
        blackboard_path = tmp_path / "blackboard.json"
        blackboard = BlackboardCommunication(blackboard_path)

        # Post different types of messages
        blackboard.post_message("agent_1", "Info message", "info")
        blackboard.post_message("agent_2", "Error message", "error")
        blackboard.post_message("agent_3", "Result message", "result")

        # Filter by type
        error_messages = blackboard.get_messages(message_type="error")
        assert len(error_messages) == 1
        assert error_messages[0]["type"] == "error"

    def test_blackboard_shared_data(self, tmp_path):
        """Test blackboard shared data."""
        blackboard_path = tmp_path / "blackboard.json"
        blackboard = BlackboardCommunication(blackboard_path)

        # Set shared data
        blackboard.set_shared_data("current_task", "Refactoring")
        blackboard.set_shared_data("progress", 50)

        # Get shared data
        task = blackboard.get_shared_data("current_task")
        progress = blackboard.get_shared_data("progress")

        assert task == "Refactoring"
        assert progress == 50

    def test_blackboard_clear(self, tmp_path):
        """Test blackboard clearing."""
        blackboard_path = tmp_path / "blackboard.json"
        blackboard = BlackboardCommunication(blackboard_path)

        # Add data
        blackboard.post_message("agent_1", "Message", "info")
        blackboard.set_shared_data("key", "value")

        # Clear
        blackboard.clear()

        # Verify cleared
        messages = blackboard.get_messages()
        assert len(messages) == 0

        data = blackboard.get_shared_data("key")
        assert data is None


class TestAgenticCommands:
    """Test agentic commands."""

    def test_plan_command_creation(self):
        """Test plan command creation."""
        config = Config()
        command = PlanCommand(config)

        assert command.name == "/plan"
        assert "plan" in command.description.lower()

    def test_improve_command_creation(self):
        """Test improve command creation."""
        config = Config()
        command = ImproveCommand(config)

        assert command.name == "/improve"
        assert "improve" in command.description.lower()

    def test_spawn_command_creation(self):
        """Test spawn command creation."""
        config = Config()
        command = SpawnCommand(config)

        assert command.name == "/spawn"
        assert "spawn" in command.description.lower()

    def test_episodes_command_creation(self):
        """Test episodes command creation."""
        config = Config()
        command = EpisodesCommand(config)

        assert command.name == "/episodes"
        assert "episode" in command.description.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
