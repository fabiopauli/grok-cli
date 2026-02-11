#!/usr/bin/env python3

"""
Tests for Context Deduplication in File Tools

Tests that ReadFileTool and ReadMultipleFilesTool properly deduplicate
files that are already in context.
"""

from unittest.mock import Mock

import pytest

from src.core.config import Config
from src.tools.file_tools import ReadFileTool, ReadMultipleFilesTool


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config for testing."""
    config = Mock(spec=Config)
    config.base_dir = tmp_path
    config.use_relative_paths = False
    config.compact_tool_results = False
    config.excluded_files = set()
    config.excluded_extensions = set()
    config.current_model = "grok-2"
    config.get_max_tokens_for_model = Mock(return_value=100000)
    config.deduplicate_file_content = True
    return config


@pytest.fixture
def mock_context_manager():
    """Create a mock context manager for testing."""
    context_manager = Mock()
    context_manager.is_file_in_context = Mock(return_value=False)
    context_manager.add_file_to_context = Mock()
    return context_manager


@pytest.fixture
def test_file(tmp_path):
    """Create a test file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("This is test content for deduplication testing.")
    return test_file


class TestReadFileToolDeduplication:
    """Test ReadFileTool deduplication behavior."""

    def test_read_file_when_not_in_context(self, mock_config, mock_context_manager, test_file):
        """Test that file is read normally when not in context."""
        tool = ReadFileTool(mock_config)
        tool.context_manager = mock_context_manager

        # File is NOT in context
        mock_context_manager.is_file_in_context.return_value = False

        result = tool.execute({"file_path": str(test_file)})

        assert result.success is True
        assert "This is test content" in result.result

        # Verify context manager methods were called
        mock_context_manager.is_file_in_context.assert_called_once()
        mock_context_manager.add_file_to_context.assert_called_once()

    def test_read_file_when_already_in_context(self, mock_config, mock_context_manager, test_file):
        """Test that file returns short message when already in context."""
        tool = ReadFileTool(mock_config)
        tool.context_manager = mock_context_manager

        # File IS in context
        mock_context_manager.is_file_in_context.return_value = True

        result = tool.execute({"file_path": str(test_file)})

        assert result.success is True
        assert "already available in context" in result.result.lower()
        assert "This is test content" not in result.result

        # Verify we checked if file is in context
        mock_context_manager.is_file_in_context.assert_called_once()

        # Verify we did NOT try to read or add the file
        mock_context_manager.add_file_to_context.assert_not_called()

    def test_read_file_without_context_manager(self, mock_config, test_file):
        """Test that file is read normally when context_manager is None."""
        tool = ReadFileTool(mock_config)
        tool.context_manager = None

        result = tool.execute({"file_path": str(test_file)})

        assert result.success is True
        assert "This is test content" in result.result

    def test_read_file_with_relative_paths(self, mock_config, mock_context_manager, test_file):
        """Test that relative path is used in message when config enables it."""
        mock_config.use_relative_paths = True
        tool = ReadFileTool(mock_config)
        tool.context_manager = mock_context_manager

        mock_context_manager.is_file_in_context.return_value = True

        result = tool.execute({"file_path": str(test_file)})

        assert result.success is True
        # Should show just the filename, not full path
        assert "test.txt" in result.result
        assert "already available in context" in result.result.lower()


class TestReadMultipleFilesToolDeduplication:
    """Test ReadMultipleFilesTool deduplication behavior."""

    def test_read_multiple_files_mixed_context(self, mock_config, mock_context_manager, tmp_path):
        """Test reading multiple files where some are in context and some aren't."""
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file3 = tmp_path / "file3.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")
        file3.write_text("Content 3")

        tool = ReadMultipleFilesTool(mock_config)
        tool.context_manager = mock_context_manager

        # file1 is in context, file2 and file3 are not
        def is_in_context_side_effect(path):
            return str(file1.resolve()) in path

        mock_context_manager.is_file_in_context.side_effect = is_in_context_side_effect

        result = tool.execute({
            "file_paths": [str(file1), str(file2), str(file3)]
        })

        assert result.success is True

        # Parse the JSON result
        import json
        data = json.loads(result.result)

        # file1 should have the "already in context" message
        assert "already in context" in data["files_read"][str(file1)].lower()

        # file2 and file3 should have actual content
        assert "Content 2" in data["files_read"][str(file2)]
        assert "Content 3" in data["files_read"][str(file3)]

        # Verify add_file_to_context was called for file2 and file3, but not file1
        assert mock_context_manager.add_file_to_context.call_count == 2

    def test_read_multiple_files_all_in_context(self, mock_config, mock_context_manager, tmp_path):
        """Test reading multiple files that are all in context."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        tool = ReadMultipleFilesTool(mock_config)
        tool.context_manager = mock_context_manager

        # All files are in context
        mock_context_manager.is_file_in_context.return_value = True

        result = tool.execute({
            "file_paths": [str(file1), str(file2)]
        })

        assert result.success is True

        import json
        data = json.loads(result.result)

        # Both should have the "already in context" message
        assert "already in context" in data["files_read"][str(file1)].lower()
        assert "already in context" in data["files_read"][str(file2)].lower()

        # No files should have been read or added
        assert mock_context_manager.add_file_to_context.call_count == 0

    def test_read_multiple_files_none_in_context(self, mock_config, mock_context_manager, tmp_path):
        """Test reading multiple files that are not in context."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        tool = ReadMultipleFilesTool(mock_config)
        tool.context_manager = mock_context_manager

        # No files are in context
        mock_context_manager.is_file_in_context.return_value = False

        result = tool.execute({
            "file_paths": [str(file1), str(file2)]
        })

        assert result.success is True

        import json
        data = json.loads(result.result)

        # Both should have actual content
        assert "Content 1" in data["files_read"][str(file1)]
        assert "Content 2" in data["files_read"][str(file2)]

        # Both files should have been added to context
        assert mock_context_manager.add_file_to_context.call_count == 2


class TestDeduplicationConfigFlag:
    """Test that deduplication respects the config flag."""

    def test_deduplication_disabled_in_context_manager(self, mock_config, tmp_path, test_file):
        """Test that when deduplication is disabled, is_file_in_context returns False."""
        # This tests the context_manager behavior, not the tool directly
        from src.core.context_manager import ContextManager

        # Disable deduplication
        mock_config.deduplicate_file_content = False

        context_manager = ContextManager(mock_config)

        # Add file to tracking
        context_manager.add_file_to_context(str(test_file))

        # With deduplication disabled, should return False even if tracked
        assert context_manager.is_file_in_context(str(test_file)) is False

    def test_deduplication_enabled_in_context_manager(self, mock_config, tmp_path, test_file):
        """Test that when deduplication is enabled, is_file_in_context returns True."""
        from src.core.context_manager import ContextManager

        # Enable deduplication (default)
        mock_config.deduplicate_file_content = True

        context_manager = ContextManager(mock_config)

        # Add file to tracking
        context_manager.add_file_to_context(str(test_file))

        # With deduplication enabled, should return True
        assert context_manager.is_file_in_context(str(test_file)) is True
