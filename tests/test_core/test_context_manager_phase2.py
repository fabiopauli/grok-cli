#!/usr/bin/env python3

"""
Tests for Token Optimization (Deduplication)

This test suite validates:
1. File content deduplication tracking
2. System message deduplication
3. Integration with config flags
"""

from pathlib import Path

import pytest

from src.core.config import Config
from src.core.context_manager import ContextManager


class TestFileDeduplication:
    """Test file content deduplication tracking."""

    def test_add_file_to_context_without_config_flag(self):
        """Files should not be tracked when config flag is disabled."""
        config = Config()
        # Disable file deduplication
        config.deduplicate_file_content = False

        context_manager = ContextManager(config)

        # Add file to tracking
        context_manager.add_file_to_context("/path/to/file.py")

        # Should return False because flag is not enabled
        assert not context_manager.is_file_in_context("/path/to/file.py")
        assert len(context_manager._files_in_context) == 0

    def test_add_file_to_context_with_config_flag_enabled(self):
        """Files should be tracked when config flag is enabled."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Add file to tracking
        context_manager.add_file_to_context("/path/to/file.py")

        # Should be tracked
        assert context_manager.is_file_in_context("/path/to/file.py")
        assert len(context_manager._files_in_context) == 1

    def test_add_file_to_context_normalizes_paths(self):
        """File paths should be normalized (absolute) when tracking."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Add relative path
        context_manager.add_file_to_context("./relative/path.py")

        # Check with absolute path
        absolute_path = str(Path("./relative/path.py").resolve())
        assert absolute_path in context_manager._files_in_context

    def test_is_file_in_context_checks_mounted_files(self):
        """is_file_in_context should check both tracked and mounted files."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Mount a file (which also tracks it)
        context_manager.mount_file("/path/to/mounted.py", "content")

        # Should return True for mounted file
        assert context_manager.is_file_in_context("/path/to/mounted.py")

    def test_mount_file_automatically_tracks(self):
        """Mounting a file should automatically track it."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Mount a file
        test_path = "/path/to/file.py"
        context_manager.mount_file(test_path, "content")

        # Should be tracked
        assert context_manager.is_file_in_context(test_path)
        # Should also be in mounted files
        normalized_path = str(Path(test_path).resolve())
        assert normalized_path in context_manager.mounted_files

    def test_clear_file_tracking(self):
        """clear_file_tracking should remove all tracked files."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Add some files
        context_manager.add_file_to_context("/path/to/file1.py")
        context_manager.add_file_to_context("/path/to/file2.py")
        assert len(context_manager._files_in_context) == 2

        # Clear tracking
        context_manager.clear_file_tracking()

        # Should be empty
        assert len(context_manager._files_in_context) == 0

    def test_clear_context_clears_file_tracking(self):
        """clear_context should clear file tracking when mounted files are cleared."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Add files and mount files
        context_manager.add_file_to_context("/path/to/tracked.py")
        context_manager.mount_file("/path/to/mounted.py", "content")

        # Clear context without keeping mounted files
        context_manager.clear_context(keep_mounted_files=False)

        # File tracking should be cleared
        assert len(context_manager._files_in_context) == 0
        assert len(context_manager.mounted_files) == 0

    def test_clear_context_preserves_tracking_when_keeping_mounted_files(self):
        """clear_context should preserve tracking when keeping mounted files."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Mount a file
        context_manager.mount_file("/path/to/mounted.py", "content")

        # Clear context but keep mounted files
        context_manager.clear_context(keep_mounted_files=True)

        # Mounted files should remain
        assert len(context_manager.mounted_files) == 1
        # But tracking is NOT cleared when keeping mounted files
        # (because mounted files are still in context)


class TestSystemMessageDeduplication:
    """Test system message deduplication."""

    def test_add_system_message_new_message(self):
        """Adding a new system message should succeed."""
        config = Config()
        context_manager = ContextManager(config)

        # Add a new message
        result = context_manager.add_system_message("This is a system message")

        # Should return True (added)
        assert result is True
        assert len(context_manager._system_messages) == 1
        assert len(context_manager._system_message_hashes) == 1

    def test_add_system_message_duplicate(self):
        """Adding a duplicate system message should be skipped."""
        config = Config()
        context_manager = ContextManager(config)

        # Add a message
        message = "This is a system message"
        result1 = context_manager.add_system_message(message)
        assert result1 is True

        # Add the same message again
        result2 = context_manager.add_system_message(message)

        # Should return False (duplicate)
        assert result2 is False
        # Should only have one message
        assert len(context_manager._system_messages) == 1
        assert len(context_manager._system_message_hashes) == 1

    def test_add_system_message_different_messages(self):
        """Adding different system messages should all succeed."""
        config = Config()
        context_manager = ContextManager(config)

        # Add multiple different messages
        result1 = context_manager.add_system_message("Message 1")
        result2 = context_manager.add_system_message("Message 2")
        result3 = context_manager.add_system_message("Message 3")

        # All should succeed
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert len(context_manager._system_messages) == 3
        assert len(context_manager._system_message_hashes) == 3

    def test_add_system_message_similar_but_different(self):
        """Similar messages with slight differences should all be added."""
        config = Config()
        context_manager = ContextManager(config)

        # Add similar messages
        result1 = context_manager.add_system_message("Message A")
        result2 = context_manager.add_system_message("Message B")  # Different letter
        result3 = context_manager.add_system_message("Message A ")  # Extra space

        # All should succeed (different hashes)
        assert result1 is True
        assert result2 is True
        assert result3 is True
        assert len(context_manager._system_messages) == 3

    def test_clear_context_clears_system_message_hashes(self):
        """clear_context should clear system message hashes."""
        config = Config()
        context_manager = ContextManager(config)

        # Add some system messages
        context_manager.add_system_message("Message 1")
        context_manager.add_system_message("Message 2")
        assert len(context_manager._system_message_hashes) == 2

        # Clear context
        context_manager.clear_context()

        # Hashes should be cleared
        assert len(context_manager._system_message_hashes) == 0
        assert len(context_manager._system_messages) == 0

    def test_duplicate_detection_after_clear(self):
        """After clearing, same message should be addable again."""
        config = Config()
        context_manager = ContextManager(config)

        # Add a message
        message = "Test message"
        result1 = context_manager.add_system_message(message)
        assert result1 is True

        # Try to add duplicate (should fail)
        result2 = context_manager.add_system_message(message)
        assert result2 is False

        # Clear context
        context_manager.clear_context()

        # Should be able to add the same message again
        result3 = context_manager.add_system_message(message)
        assert result3 is True
        assert len(context_manager._system_messages) == 1


class TestBackwardCompatibility:
    """Test backward compatibility of deduplication features."""

    def test_deduplication_gracefully_disabled_without_config(self):
        """Deduplication should gracefully disable if config flag is False."""
        config = Config()
        # Disable file deduplication
        config.deduplicate_file_content = False

        context_manager = ContextManager(config)

        # Methods should still work, just not track
        context_manager.add_file_to_context("/path/to/file.py")
        assert not context_manager.is_file_in_context("/path/to/file.py")

        # Should not raise errors
        context_manager.clear_file_tracking()

    def test_system_message_deduplication_always_active(self):
        """System message deduplication should always be active."""
        config = Config()
        context_manager = ContextManager(config)

        # Should deduplicate regardless of config flags
        message = "Test message"
        result1 = context_manager.add_system_message(message)
        result2 = context_manager.add_system_message(message)

        assert result1 is True
        assert result2 is False


class TestIntegrationScenarios:
    """Test integration scenarios for deduplication."""

    def test_mount_and_track_multiple_files(self):
        """Mounting multiple files should track all of them."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Mount multiple files
        files = [
            ("/path/to/file1.py", "content1"),
            ("/path/to/file2.py", "content2"),
            ("/path/to/file3.py", "content3"),
        ]

        for path, content in files:
            context_manager.mount_file(path, content)

        # All should be tracked
        for path, _ in files:
            assert context_manager.is_file_in_context(path)

        # Check counts
        assert len(context_manager.mounted_files) == 3

    def test_system_message_deduplication_across_turns(self):
        """System messages should deduplicate across multiple turns."""
        config = Config()
        context_manager = ContextManager(config)

        # Add same system message multiple times across turns
        message = "Important system message"

        results = []
        for _ in range(5):
            result = context_manager.add_system_message(message)
            results.append(result)

        # Only first should succeed
        assert results == [True, False, False, False, False]
        assert len(context_manager._system_messages) == 1

    def test_file_tracking_with_path_variations(self):
        """File tracking should handle path variations correctly."""
        config = Config()
        config.deduplicate_file_content = True

        context_manager = ContextManager(config)

        # Add file with relative path
        context_manager.add_file_to_context("./test.py")

        # Check with different path representations
        absolute = str(Path("./test.py").resolve())

        # Checking with absolute path should work
        assert context_manager.is_file_in_context(absolute)
        # Checking with relative path should also work (gets normalized)
        assert context_manager.is_file_in_context("./test.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
