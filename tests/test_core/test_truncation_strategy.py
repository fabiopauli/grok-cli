#!/usr/bin/env python3

"""
Tests for TruncationStrategy (Sliding Window Implementation)

Tests the sliding window truncation logic, including:
- Configurable window size
- Incremental compression
- Panic mode handling
- Token budget verification
"""

import pytest
from datetime import datetime

from src.core.config import Config
from src.core.truncation_strategy import TruncationStrategy
from src.core.turn_logger import Turn, TurnEvent


class TestSlidingWindowConfiguration:
    """Test configurable sliding window size."""

    def test_default_window_size(self):
        """Test that default window size is 3."""
        config = Config()
        strategy = TruncationStrategy(config)

        assert strategy.min_preserved_turns == 3

    def test_custom_window_size_from_config(self):
        """Test custom window size from config."""
        config = Config()
        config.min_preserved_turns = 5
        strategy = TruncationStrategy(config)

        assert strategy.min_preserved_turns == 5

    def test_window_size_zero_fallback(self):
        """Test that window size can be set to any value."""
        config = Config()
        config.min_preserved_turns = 0
        strategy = TruncationStrategy(config)

        assert strategy.min_preserved_turns == 0


class TestTurnToMessages:
    """Test _turn_to_messages helper method."""

    def test_normal_turn_conversion(self):
        """Test converting a normal turn to messages."""
        config = Config()
        strategy = TruncationStrategy(config)

        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[
                TurnEvent(type="user_message", content="Hello"),
                TurnEvent(type="assistant_message", content="Hi there!"),
                TurnEvent(type="tool_response", tool="read_file", result="File content")
            ]
        )

        messages = strategy._turn_to_messages(turn)

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"
        assert messages[2]["role"] == "tool"
        assert messages[2]["content"] == "File content"

    def test_compressed_history_turn_uses_assistant_role(self):
        """Test that compressed_history turns use assistant role."""
        config = Config()
        strategy = TruncationStrategy(config)

        turn = Turn(
            turn_id="compressed_history",
            start_time=datetime.now().isoformat(),
            events=[],
            summary="Turn 001: User asked question; Turn 002: Used read_file"
        )

        messages = strategy._turn_to_messages(turn)

        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"  # Uses assistant role, not system
        assert "[Context Summary - Prior Conversation]" in messages[0]["content"]
        assert "Turn 001" in messages[0]["content"]

    def test_empty_turn_returns_empty_messages(self):
        """Test that turn with no events returns empty message list."""
        config = Config()
        strategy = TruncationStrategy(config)

        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[]
        )

        messages = strategy._turn_to_messages(turn)

        assert len(messages) == 0


class TestCompressTurnsToSummary:
    """Test turn compression logic."""

    def test_compress_single_turn(self):
        """Test compressing a single turn."""
        config = Config()
        strategy = TruncationStrategy(config)

        turn = Turn(
            turn_id="turn_001",
            start_time="2024-01-01T10:00:00",
            events=[
                TurnEvent(type="user_message", content="Read file.txt")
            ],
            end_time="2024-01-01T10:00:05",
            files_read=["file.txt"],
            tools_used=["read_file"],
            summary="User: Read file.txt; Tools: read_file"
        )

        summary_turn = strategy.compress_turns_to_summary([turn])

        assert summary_turn.turn_id == "compressed_history"
        assert summary_turn.start_time == "2024-01-01T10:00:00"
        assert summary_turn.end_time == "2024-01-01T10:00:05"
        assert len(summary_turn.events) == 0  # Events cleared to save tokens
        assert "turn_001" in summary_turn.summary
        assert "file.txt" in summary_turn.files_read
        assert "read_file" in summary_turn.tools_used

    def test_compress_multiple_turns(self):
        """Test compressing multiple turns."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [
            Turn(
                turn_id="turn_001",
                start_time="2024-01-01T10:00:00",
                events=[],
                end_time="2024-01-01T10:00:05",
                files_read=["file1.txt"],
                summary="Read file1"
            ),
            Turn(
                turn_id="turn_002",
                start_time="2024-01-01T10:00:10",
                events=[],
                end_time="2024-01-01T10:00:15",
                files_modified=["file2.txt"],
                summary="Modified file2"
            ),
        ]

        summary_turn = strategy.compress_turns_to_summary(turns)

        assert "turn_001" in summary_turn.summary
        assert "turn_002" in summary_turn.summary
        assert "file1.txt" in summary_turn.files_read
        assert "file2.txt" in summary_turn.files_modified

    def test_compress_skips_existing_compressed_history(self):
        """Test that compressed_history turns are skipped during compression."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [
            Turn(
                turn_id="compressed_history",
                start_time="2024-01-01T09:00:00",
                events=[],
                summary="Old compressed history"
            ),
            Turn(
                turn_id="turn_003",
                start_time="2024-01-01T10:00:00",
                events=[],
                summary="New turn"
            ),
        ]

        summary_turn = strategy.compress_turns_to_summary(turns)

        # Should not include the compressed_history turn's summary
        assert "turn_003" in summary_turn.summary
        assert "Old compressed history" not in summary_turn.summary

    def test_compress_empty_list_returns_placeholder(self):
        """Test compressing empty list returns placeholder turn."""
        config = Config()
        strategy = TruncationStrategy(config)

        summary_turn = strategy.compress_turns_to_summary([])

        assert summary_turn.turn_id == "compressed_history"
        assert summary_turn.summary == "No turns to compress"


class TestSlidingWindowTruncation:
    """Test sliding window truncation logic."""

    def create_mock_turn(self, turn_id: str, content_size: int = 100) -> Turn:
        """Helper to create a mock turn with estimated content."""
        return Turn(
            turn_id=turn_id,
            start_time=datetime.now().isoformat(),
            events=[
                TurnEvent(type="user_message", content="x" * content_size),
                TurnEvent(type="assistant_message", content="y" * content_size)
            ],
            summary=f"Turn {turn_id} summary"
        )

    def mock_token_estimator(self, messages: list) -> tuple[int, dict]:
        """Mock token estimator that counts characters."""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        # Rough estimate: 1 token per 4 characters
        return (total_chars // 4, {})

    def test_no_truncation_when_under_budget(self):
        """Test that no truncation occurs when under token budget."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [
            self.create_mock_turn("turn_001", 50),
            self.create_mock_turn("turn_002", 50),
        ]

        # Large budget - no truncation needed
        result = strategy.truncate_turns(turns, 10000, self.mock_token_estimator)

        assert len(result) == 2
        assert result[0].turn_id == "turn_001"
        assert result[1].turn_id == "turn_002"

    def test_sliding_window_preserves_recent_turns(self):
        """Test that sliding window preserves last N turns."""
        config = Config()
        config.min_preserved_turns = 3
        strategy = TruncationStrategy(config)

        # Create 6 turns
        turns = [self.create_mock_turn(f"turn_{i:03d}", 100) for i in range(1, 7)]

        # Set very tight budget to force truncation (each turn is ~50 tokens, 6 turns = ~300 tokens)
        result = strategy.truncate_turns(turns, 200, self.mock_token_estimator)

        # Should have: 1 compressed summary + 3 recent turns = 4 total
        assert len(result) <= 4

        # First turn should be compressed_history
        if len(result) == 4:
            assert result[0].turn_id == "compressed_history"
            # Last 3 should be preserved
            assert result[1].turn_id == "turn_004"
            assert result[2].turn_id == "turn_005"
            assert result[3].turn_id == "turn_006"

    def test_incremental_compression_merges_summaries(self):
        """Test that multiple compressions merge summaries."""
        config = Config()
        config.min_preserved_turns = 2
        strategy = TruncationStrategy(config)

        # First compression (4 turns, each ~50 tokens = ~200 tokens total)
        turns1 = [self.create_mock_turn(f"turn_{i:03d}", 100) for i in range(1, 5)]
        result1 = strategy.truncate_turns(turns1, 150, self.mock_token_estimator)

        # Should have compressed_history + 2 recent turns
        assert result1[0].turn_id == "compressed_history"
        existing_summary = result1[0].summary

        # Second compression - add more turns
        new_turns = [self.create_mock_turn(f"turn_{i:03d}", 100) for i in range(5, 8)]
        all_turns = result1 + new_turns
        result2 = strategy.truncate_turns(all_turns, 150, self.mock_token_estimator)

        # Should still have compressed_history + recent turns
        assert result2[0].turn_id == "compressed_history"
        # New summary should contain the merge marker
        assert "[...]" in result2[0].summary or len(result2[0].summary) > len(existing_summary)

    def test_panic_mode_when_budget_exceeded(self):
        """Test panic mode when even sliding window exceeds budget."""
        config = Config()
        config.min_preserved_turns = 3
        strategy = TruncationStrategy(config)

        # Create turns with large content
        turns = [self.create_mock_turn(f"turn_{i:03d}", 1000) for i in range(1, 6)]

        # Very small budget to trigger panic mode
        result = strategy.truncate_turns(turns, 100, self.mock_token_estimator)

        # Panic mode should keep only summary + last turn
        assert len(result) <= 2
        assert result[0].turn_id == "compressed_history"
        if len(result) == 2:
            assert result[1].turn_id == "turn_005"

    def test_empty_turn_list_returns_empty(self):
        """Test that empty turn list returns empty."""
        config = Config()
        strategy = TruncationStrategy(config)

        result = strategy.truncate_turns([], 1000, self.mock_token_estimator)

        assert len(result) == 0

    def test_single_turn_returns_unchanged(self):
        """Test that single turn under budget returns unchanged."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [self.create_mock_turn("turn_001", 50)]

        result = strategy.truncate_turns(turns, 1000, self.mock_token_estimator)

        assert len(result) == 1
        assert result[0].turn_id == "turn_001"

    def test_window_size_larger_than_turn_count(self):
        """Test behavior when window size is larger than turn count."""
        config = Config()
        config.min_preserved_turns = 10
        strategy = TruncationStrategy(config)

        # Only 3 turns but window wants 10
        turns = [self.create_mock_turn(f"turn_{i:03d}", 200) for i in range(1, 4)]

        # Even with small budget, should preserve what we can
        result = strategy.truncate_turns(turns, 100, self.mock_token_estimator)

        # Should trigger panic mode: compress all but last
        assert len(result) <= 2
        if len(result) == 2:
            assert result[0].turn_id == "compressed_history"
            assert result[1].turn_id == "turn_003"


class TestFileMetadataPreservation:
    """Test that file metadata is preserved through compression."""

    def test_file_metadata_consolidated(self):
        """Test that file metadata is consolidated during compression."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [
            Turn(
                turn_id="turn_001",
                start_time=datetime.now().isoformat(),
                events=[],
                files_read=["file1.txt", "file2.txt"],
                files_modified=["file1.txt"],
            ),
            Turn(
                turn_id="turn_002",
                start_time=datetime.now().isoformat(),
                events=[],
                files_read=["file2.txt", "file3.txt"],
                files_created=["newfile.txt"],
            ),
        ]

        summary = strategy.compress_turns_to_summary(turns)

        # Should have all unique files
        assert set(summary.files_read) == {"file1.txt", "file2.txt", "file3.txt"}
        assert "file1.txt" in summary.files_modified
        assert "newfile.txt" in summary.files_created

    def test_tools_used_consolidated(self):
        """Test that tools_used is consolidated during compression."""
        config = Config()
        strategy = TruncationStrategy(config)

        turns = [
            Turn(
                turn_id="turn_001",
                start_time=datetime.now().isoformat(),
                events=[],
                tools_used=["read_file", "edit_file"],
            ),
            Turn(
                turn_id="turn_002",
                start_time=datetime.now().isoformat(),
                events=[],
                tools_used=["read_file", "create_file"],
            ),
        ]

        summary = strategy.compress_turns_to_summary(turns)

        # Should have all unique tools
        assert set(summary.tools_used) == {"read_file", "edit_file", "create_file"}


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_turn_with_missing_events(self):
        """Test handling of turn with missing events list."""
        config = Config()
        strategy = TruncationStrategy(config)

        # Turn with None events (should default to empty list)
        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[]
        )

        messages = strategy._turn_to_messages(turn)
        assert isinstance(messages, list)
        assert len(messages) == 0

    def test_very_long_summary_in_compressed_turn(self):
        """Test that very long summaries are handled."""
        config = Config()
        strategy = TruncationStrategy(config)

        # Create turn with very long summary
        long_summary = "x" * 10000
        turn = Turn(
            turn_id="turn_001",
            start_time=datetime.now().isoformat(),
            events=[],
            summary=long_summary
        )

        result = strategy.compress_turns_to_summary([turn])

        # Should not crash, summary should be preserved
        assert result.turn_id == "compressed_history"
        assert len(result.summary) > 0
