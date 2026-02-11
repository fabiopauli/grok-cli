#!/usr/bin/env python3

"""
Tests for Structured Summarization (Fix B)

This test suite validates the structured state-based summarization that
replaces lossy text-based summaries with structured data objects.

Test Coverage:
1. ContextState creation and merging
2. State serialization/deserialization
3. Turn compression to structured state
4. State message formatting
5. Entropy prevention (telephone game)
6. Backward compatibility with text summaries
"""

from datetime import datetime

from src.core.context_state import ContextState
from src.core.truncation_strategy import TruncationStrategy
from src.core.turn_logger import Turn, TurnEvent


class TestContextState:
    """Test ContextState creation and operations."""

    def test_context_state_creation(self):
        """Test creating an empty ContextState."""
        state = ContextState()

        assert state.is_empty()
        assert len(state.files_modified) == 0
        assert len(state.tasks_completed) == 0
        assert state.main_goal == ""

    def test_context_state_with_data(self):
        """Test creating ContextState with data."""
        state = ContextState(
            files_modified={'test.py', 'main.py'},
            files_created={'new.py'},
            tasks_completed=['Fixed bug in login'],
            main_goal='Implement authentication'
        )

        assert not state.is_empty()
        assert 'test.py' in state.files_modified
        assert 'new.py' in state.files_created
        assert len(state.tasks_completed) == 1
        assert state.main_goal == 'Implement authentication'

    def test_context_state_merge(self):
        """Test merging two ContextState objects."""
        state1 = ContextState(
            files_modified={'file1.py'},
            tasks_completed=['Task 1']
        )

        state2 = ContextState(
            files_modified={'file2.py'},
            tasks_completed=['Task 2'],
            main_goal='New goal'
        )

        state1.merge(state2)

        # Verify merge
        assert 'file1.py' in state1.files_modified
        assert 'file2.py' in state1.files_modified
        assert len(state1.tasks_completed) == 2
        assert state1.main_goal == 'New goal'

    def test_context_state_serialization(self):
        """Test JSON serialization/deserialization."""
        original = ContextState(
            files_modified={'test.py'},
            files_created={'new.py'},
            tasks_completed=['Completed task'],
            main_goal='Test goal'
        )

        # Serialize to JSON
        json_str = original.to_json()
        assert isinstance(json_str, str)
        assert 'test.py' in json_str

        # Deserialize from JSON
        restored = ContextState.from_json(json_str)

        assert 'test.py' in restored.files_modified
        assert 'new.py' in restored.files_created
        assert restored.tasks_completed == ['Completed task']
        assert restored.main_goal == 'Test goal'

    def test_context_state_to_context_message(self):
        """Test converting state to context message."""
        state = ContextState(
            files_modified={'login.py'},
            tasks_completed=['Fixed authentication bug'],
            main_goal='Implement user system'
        )

        message = state.to_context_message()

        assert isinstance(message, str)
        assert 'Current Objective' in message
        assert 'Implement user system' in message
        assert 'login.py' in message
        assert 'Fixed authentication bug' in message

    def test_empty_state_message(self):
        """Test that empty state produces empty message."""
        state = ContextState()
        message = state.to_context_message()

        # Empty state should produce empty message
        assert message == ""

    def test_state_summary_stats(self):
        """Test getting summary statistics."""
        state = ContextState(
            files_modified={'f1.py', 'f2.py'},
            files_created={'f3.py'},
            tasks_completed=['t1', 't2', 't3'],
            tools_used={'edit_file', 'read_file'}
        )

        stats = state.get_summary_stats()

        assert stats['files_modified'] == 2
        assert stats['files_created'] == 1
        assert stats['tasks_completed'] == 3
        assert stats['tools_used'] == 2


class TestTruncationStrategyStructuredState:
    """Test TruncationStrategy's structured state compression."""

    def test_extract_state_from_turn(self, mock_config):
        """Test extracting state from a single turn."""
        strategy = TruncationStrategy(mock_config)

        # Create a turn with file operations
        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[
                TurnEvent(type="user_message", content="Fix the bug in login.py"),
                TurnEvent(type="assistant_message", content="I'll fix it"),
            ],
            end_time=datetime.now().isoformat(),
            files_modified=['login.py'],
            files_created=[],
            files_read=['config.py'],
            tools_used=['edit_file', 'read_file'],
            summary='Fixed authentication bug'
        )

        state = strategy.extract_state_from_turn(turn)

        assert 'login.py' in state.files_modified
        assert 'config.py' in state.files_read
        assert 'edit_file' in state.tools_used
        assert 'Fixed authentication bug' in state.tasks_completed

    def test_compress_turns_to_state(self, mock_config):
        """Test compressing multiple turns into structured state."""
        strategy = TruncationStrategy(mock_config)

        # Create multiple turns
        turn1 = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['file1.py'],
            files_read=['file2.py'],
            tools_used=['edit_file'],
            summary='Modified file1'
        )

        turn2 = Turn(
            turn_id="turn_002",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['file3.py'],
            files_created=['file4.py'],
            tools_used=['create_file'],
            summary='Created file4'
        )

        state = strategy.compress_turns_to_state([turn1, turn2])

        # Verify state contains info from both turns
        assert 'file1.py' in state.files_modified
        assert 'file3.py' in state.files_modified
        assert 'file2.py' in state.files_read
        assert 'file4.py' in state.files_created
        assert 'edit_file' in state.tools_used
        assert 'create_file' in state.tools_used

    def test_state_to_turn_conversion(self, mock_config):
        """Test converting ContextState to Turn and back."""
        strategy = TruncationStrategy(mock_config)

        # Create a state
        original_state = ContextState(
            files_modified={'test.py'},
            tasks_completed=['Task done'],
            main_goal='Test goal'
        )

        # Convert to turn
        turn = strategy.state_to_turn(original_state)

        assert turn.turn_id == "compressed_state"
        assert "[STRUCTURED_STATE]" in turn.summary

        # Convert back to state
        restored_state = strategy.turn_to_state(turn)

        assert restored_state is not None
        assert 'test.py' in restored_state.files_modified
        assert restored_state.tasks_completed == ['Task done']
        assert restored_state.main_goal == 'Test goal'

    def test_turn_to_messages_with_state(self, mock_config):
        """Test converting state turn to messages."""
        strategy = TruncationStrategy(mock_config)

        state = ContextState(
            files_modified={'login.py'},
            main_goal='Implement auth'
        )

        turn = strategy.state_to_turn(state)
        messages = strategy._turn_to_messages(turn)

        assert len(messages) == 1
        assert messages[0]['role'] == 'assistant'
        assert '[Context State - Prior Work]' in messages[0]['content']
        assert 'login.py' in messages[0]['content']


class TestStructuredVsTextSummarization:
    """Test comparison between structured and text-based summarization."""

    def test_text_summarization_entropy(self, mock_config):
        """Demonstrate entropy in text-based summarization (telephone game)."""
        # Disable structured state to test legacy behavior
        config = mock_config
        config.use_structured_state = False
        strategy = TruncationStrategy(config)

        # Create initial turn
        turn1 = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['auth.py'],
            summary='Fixed login bug in auth.py line 42'
        )

        # Compress to text summary
        summary_turn = strategy.compress_turns_to_summary([turn1])

        # Verify turn was compressed with text summary
        assert summary_turn.turn_id == "compressed_history"
        assert 'Turn turn_001' in summary_turn.summary

        # Compress again (simulating multiple truncations)
        # Note: compressed_history turns are skipped in compress_turns_to_summary
        # so we need to create a new turn to compress along with it
        turn2 = Turn(
            turn_id="turn_002",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['user.py'],
            summary='Added user validation'
        )

        summary_turn2 = strategy.compress_turns_to_summary([summary_turn, turn2])

        # Text summaries compound - shows entropy potential
        assert summary_turn2.turn_id == "compressed_history"
        # Should contain reference to the new turn
        assert 'turn_002' in summary_turn2.summary or 'user validation' in summary_turn2.summary.lower()

    def test_structured_state_no_entropy(self, mock_config):
        """Demonstrate that structured state prevents entropy."""
        # Enable structured state
        config = mock_config
        config.use_structured_state = True
        strategy = TruncationStrategy(config)

        # Create initial turn
        turn1 = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['auth.py'],
            summary='Fixed login bug in auth.py line 42'
        )

        # Compress to structured state
        state1 = strategy.compress_turns_to_state([turn1])

        # Compress again (simulating multiple truncations)
        state_turn = strategy.state_to_turn(state1)
        state2 = strategy.turn_to_state(state_turn)

        # State remains identical (no entropy)
        assert state2 is not None
        assert 'auth.py' in state2.files_modified
        # Files set doesn't duplicate
        assert len(state2.files_modified) == 1

    def test_incremental_state_merging(self, mock_config):
        """Test that states merge without duplication."""
        config = mock_config
        config.use_structured_state = True
        strategy = TruncationStrategy(config)

        # Create state from first batch of turns
        turn1 = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['file1.py'],
            summary='Modified file1'
        )

        state1 = strategy.compress_turns_to_state([turn1])

        # Create second batch
        turn2 = Turn(
            turn_id="turn_002",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['file2.py'],
            summary='Modified file2'
        )

        state2 = strategy.compress_turns_to_state([turn2])

        # Merge states
        state1.merge(state2)

        # Verify no duplication, clean merge
        assert 'file1.py' in state1.files_modified
        assert 'file2.py' in state1.files_modified
        assert len(state1.files_modified) == 2


class TestBackwardCompatibility:
    """Test backward compatibility with text-based summarization."""

    def test_can_disable_structured_state(self, mock_config):
        """Test that structured state can be disabled for legacy behavior."""
        config = mock_config
        config.use_structured_state = False

        strategy = TruncationStrategy(config)

        assert not strategy.use_structured_state

    def test_text_summarization_still_works(self, mock_config):
        """Test that text-based summarization still works when disabled."""
        config = mock_config
        config.use_structured_state = False
        strategy = TruncationStrategy(config)

        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            summary='Test summary'
        )

        summary_turn = strategy.compress_turns_to_summary([turn])

        assert summary_turn.turn_id == "compressed_history"
        assert 'Test summary' in summary_turn.summary

    def test_truncate_uses_correct_mode(self, mock_config):
        """Test that truncate_turns uses correct compression mode."""
        # Create turns that need truncation
        turns = []
        for i in range(10):
            turn = Turn(
                turn_id=f"turn_{i:03d}",
                start_time=datetime.now().isoformat(),
                events=[
                    TurnEvent(type="user_message", content=f"Message {i}"),
                    TurnEvent(type="assistant_message", content=f"Response {i}")
                ],
                files_modified=[f'file{i}.py']
            )
            turns.append(turn)

        # Test with structured state enabled
        config1 = mock_config
        config1.use_structured_state = True
        strategy1 = TruncationStrategy(config1)

        def dummy_estimator(messages):
            return (len(str(messages)), {})

        truncated1 = strategy1.truncate_turns(turns, target_tokens=500, token_estimator=dummy_estimator)

        # Should have compressed_state turn
        has_state = any(t.turn_id == "compressed_state" for t in truncated1)
        assert has_state or len(truncated1) <= 3  # Or kept within window

        # Test with structured state disabled
        config2 = mock_config
        config2.use_structured_state = False
        strategy2 = TruncationStrategy(config2)

        truncated2 = strategy2.truncate_turns(turns, target_tokens=500, token_estimator=dummy_estimator)

        # Should have compressed_history turn (legacy)
        has_history = any(t.turn_id == "compressed_history" for t in truncated2)
        assert has_history or len(truncated2) <= 3  # Or kept within window


class TestIntegrationStructuredSummarization:
    """Integration tests for structured summarization."""

    def test_full_compression_cycle(self, mock_config):
        """Test complete compression cycle with structured state."""
        config = mock_config
        config.use_structured_state = True
        config.min_preserved_turns = 2
        strategy = TruncationStrategy(config)

        # Create 5 turns with file operations
        turns = []
        for i in range(5):
            turn = Turn(
                turn_id=f"turn_{i:03d}",
                start_time=datetime.now().isoformat(),
                events=[
                    TurnEvent(type="user_message", content=f"Task {i}"),
                    TurnEvent(type="assistant_message", content=f"Done {i}")
                ],
                files_modified=[f'file{i}.py'],
                tools_used=['edit_file'],
                summary=f'Completed task {i}'
            )
            turns.append(turn)

        # Truncate to compress older turns
        # Use very small target to force truncation
        def token_estimator(messages):
            # Return large token count to force truncation
            return (10000, {})

        truncated = strategy.truncate_turns(
            turns,
            target_tokens=100,  # Very small target
            token_estimator=token_estimator
        )

        # Should have compressed due to small target
        # Either compressed_state + last turn, or just within window
        assert len(truncated) <= 3  # compressed_state + 2 recent, or panic mode (state + 1)

        # Verify compression happened
        assert len(truncated) < len(turns)

        # Check if first turn is compressed state
        if truncated and truncated[0].turn_id == "compressed_state":
            state = strategy.turn_to_state(truncated[0])
            assert state is not None
            # Should have files from compressed turns
            assert len(state.files_modified) > 0

    def test_state_persists_across_truncations(self, mock_config):
        """Test that state information persists through multiple truncations."""
        config = mock_config
        config.use_structured_state = True
        strategy = TruncationStrategy(config)

        # First truncation
        turn1 = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['important.py'],
            summary='Critical file modified'
        )

        state1 = strategy.compress_turns_to_state([turn1])
        state_turn1 = strategy.state_to_turn(state1)

        # Second truncation with new turns
        turn2 = Turn(
            turn_id="turn_002",
            start_time=datetime.now().isoformat(),
            events=[],
            files_modified=['another.py']
        )

        # Simulate compression with existing state
        existing_state = strategy.turn_to_state(state_turn1)
        new_state = strategy.compress_turns_to_state([turn2])
        existing_state.merge(new_state)

        # Verify important.py still tracked
        assert 'important.py' in existing_state.files_modified
        assert 'another.py' in existing_state.files_modified
        # No duplication
        assert len(existing_state.files_modified) == 2
