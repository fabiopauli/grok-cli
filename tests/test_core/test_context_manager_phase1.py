"""
Tests for Stale Thresholds and Message Storage Unification

Tests for critical bug fixes in context management:
1. Dynamic token thresholds that update on model switch
2. Single source of truth for message storage (turn-based)
"""

import pytest
from src.core.context_manager import ContextManager
from src.core.config import Config


class TestDynamicTokenThresholds:
    """Test that token thresholds update dynamically when model changes."""

    def test_thresholds_update_on_model_switch(self, clean_config):
        """Verify thresholds update when model changes."""
        config = clean_config
        context_mgr = ContextManager(config)

        # Initial model (defaults to grok-4-1-fast-non-reasoning with 128K default)
        initial_cache_threshold = context_mgr.cache_token_threshold
        initial_smart_threshold = context_mgr.smart_truncation_threshold

        # Verify initial values with 10% buffer: effective_max = 128K * 0.9 = 115200
        # cache_threshold = 115200 * 0.9 = 103680, smart_threshold = 115200 * 0.7 = 80640
        assert initial_cache_threshold == int(128000 * 0.9 * 0.9)  # 103680
        assert initial_smart_threshold == int(128000 * 0.9 * 0.7)  # 80640

        # Switch to extended context (2M tokens)
        config.use_extended_context = True
        config.current_model = "grok-4-1-fast-non-reasoning"

        # Thresholds should now be higher
        new_cache_threshold = context_mgr.cache_token_threshold
        new_smart_threshold = context_mgr.smart_truncation_threshold

        assert new_cache_threshold > initial_cache_threshold
        assert new_smart_threshold > initial_smart_threshold
        # With 10% buffer: effective_max = 2M * 0.9 = 1.8M
        # cache = 1.8M * 0.9 = 1620000, smart = 1.8M * 0.7 = 1260000
        assert new_cache_threshold == int(2_000_000 * 0.9 * 0.9)  # 1620000
        assert new_smart_threshold == int(2_000_000 * 0.9 * 0.7)  # 1260000

    def test_thresholds_update_on_different_models(self):
        """Verify thresholds change for different model types."""
        config = Config()
        context_mgr = ContextManager(config)

        # Test with coding model (128K)
        config.current_model = "grok-code-fast-1"
        coding_threshold = context_mgr.cache_token_threshold
        # With 10% buffer: 128K * 0.9 * 0.9 = 103680
        assert coding_threshold == int(128000 * 0.9 * 0.9)

        # Test with reasoning model (2M potential, 128K default)
        config.current_model = "grok-4-1-fast-reasoning"
        config.use_extended_context = False
        reasoning_threshold = context_mgr.cache_token_threshold
        # With 10% buffer: 128K * 0.9 * 0.9 = 103680
        assert reasoning_threshold == int(128000 * 0.9 * 0.9)

        # Enable extended context
        config.use_extended_context = True
        extended_threshold = context_mgr.cache_token_threshold
        # With 10% buffer: 2M * 0.9 * 0.9 = 1620000
        assert extended_threshold == int(2_000_000 * 0.9 * 0.9)


class TestMessageStorageUnification:
    """Test that messages are stored only in TurnLogger (single source of truth)."""

    def test_full_context_derived_from_turns(self):
        """Verify full_context is derived from turn logs, not stored separately."""
        config = Config()
        context_mgr = ContextManager(config)

        # Initially, full_context should only have system messages
        initial_context = context_mgr.full_context
        assert all(msg["role"] == "system" for msg in initial_context)

        # Start a turn and add messages
        context_mgr.start_turn("Hello, assistant")
        context_mgr.add_assistant_message("Hi there! How can I help?")

        # full_context should now include these messages (derived from turn_logger)
        current_context = context_mgr.full_context
        messages_text = [msg["content"] for msg in current_context]

        assert "Hello, assistant" in messages_text
        assert "Hi there! How can I help?" in messages_text

    def test_messages_persist_after_turn_completion(self):
        """Verify messages remain accessible after turn completion."""
        config = Config()
        context_mgr = ContextManager(config)

        # Add a complete turn
        context_mgr.start_turn("What is 2+2?")
        context_mgr.add_assistant_message("2+2 equals 4")
        context_mgr.complete_turn("Math question answered")

        # Messages should still be in full_context (from turn_logs)
        context = context_mgr.full_context
        messages_text = [msg["content"] for msg in context]

        assert "What is 2+2?" in messages_text
        assert "2+2 equals 4" in messages_text

    def test_multiple_turns_accumulate(self):
        """Verify multiple turns accumulate correctly."""
        config = Config()
        context_mgr = ContextManager(config)

        # Turn 1
        context_mgr.start_turn("First question")
        context_mgr.add_assistant_message("First answer")
        context_mgr.complete_turn()

        # Turn 2
        context_mgr.start_turn("Second question")
        context_mgr.add_assistant_message("Second answer")
        context_mgr.complete_turn()

        # All messages should be present
        context = context_mgr.full_context
        messages_text = [msg["content"] for msg in context]

        assert "First question" in messages_text
        assert "First answer" in messages_text
        assert "Second question" in messages_text
        assert "Second answer" in messages_text

    def test_system_messages_stored_separately(self):
        """Verify system messages are stored in _system_messages."""
        config = Config()
        context_mgr = ContextManager(config)

        # Add system messages
        context_mgr.add_system_message("System info 1")
        context_mgr.add_system_message("System info 2")

        # System messages should be in full_context
        context = context_mgr.full_context
        system_msgs = [msg for msg in context if msg["role"] == "system"]

        assert len(system_msgs) >= 2
        system_content = [msg["content"] for msg in system_msgs]
        assert "System info 1" in system_content
        assert "System info 2" in system_content

    def test_clear_context_resets_correctly(self):
        """Verify clear_context resets all storage correctly."""
        config = Config()
        context_mgr = ContextManager(config)

        # Add various messages
        context_mgr.add_system_message("System message")
        context_mgr.start_turn("User message")
        context_mgr.add_assistant_message("Assistant message")
        context_mgr.complete_turn()

        # Clear context
        context_mgr.clear_context(keep_memories=True)

        # full_context should be empty (or only have new system messages added by clear)
        context = context_mgr.full_context
        assert len(context) == 0 or all(msg["role"] == "system" for msg in context)
        assert len(context_mgr.turn_logs) == 0


class TestBackwardCompatibility:
    """Test that existing APIs still work correctly."""

    def test_full_context_property_accessible(self):
        """Verify full_context can still be accessed like before."""
        config = Config()
        context_mgr = ContextManager(config)

        # Should be able to read full_context
        context = context_mgr.full_context
        assert isinstance(context, list)

    def test_threshold_properties_accessible(self):
        """Verify threshold properties can be accessed like before."""
        config = Config()
        context_mgr = ContextManager(config)

        # Should be able to read thresholds
        cache_threshold = context_mgr.cache_token_threshold
        smart_threshold = context_mgr.smart_truncation_threshold

        assert isinstance(cache_threshold, int)
        assert isinstance(smart_threshold, int)
        assert cache_threshold > smart_threshold  # 90% > 70%


class TestIntegrationScenarios:
    """Test real-world usage scenarios."""

    def test_model_switch_during_conversation(self, clean_config):
        """Test switching models mid-conversation with extended context."""
        config = clean_config
        context_mgr = ContextManager(config)

        # Start conversation with default model
        context_mgr.start_turn("Hello")
        context_mgr.add_assistant_message("Hi")
        context_mgr.complete_turn()

        initial_threshold = context_mgr.cache_token_threshold

        # Switch to extended context
        config.use_extended_context = True

        # Threshold should immediately reflect the change
        new_threshold = context_mgr.cache_token_threshold
        assert new_threshold > initial_threshold

        # Continue conversation with new threshold
        context_mgr.start_turn("What's 2+2?")
        context_mgr.add_assistant_message("4")
        context_mgr.complete_turn()

        # All messages should still be present
        context = context_mgr.full_context
        messages_text = [msg["content"] for msg in context]
        assert "Hello" in messages_text
        assert "What's 2+2?" in messages_text

    def test_tool_responses_in_turn_storage(self):
        """Test that tool responses are correctly stored in turns."""
        config = Config()
        context_mgr = ContextManager(config)

        # Start turn with tool usage
        context_mgr.start_turn("Read file.txt")
        context_mgr.add_tool_response("read_file", "File content: Hello World")
        context_mgr.add_assistant_message("The file contains: Hello World")
        context_mgr.complete_turn()

        # Tool response should be in context
        context = context_mgr.full_context
        tool_msgs = [msg for msg in context if msg["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert "Hello World" in tool_msgs[0]["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
