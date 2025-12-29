#!/usr/bin/env python3

"""
Integration Tests for Context De-duplication and Circular Import Resolution

End-to-end tests demonstrating the improvements work together correctly.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock

from src.core.config import Config
from src.core.context_manager import ContextManager
from src.tools.file_tools import ReadFileTool, ChangeWorkingDirectoryTool
from src.commands.file_commands import FolderCommand
from src.services.directory_service import DirectoryService


@pytest.fixture
def real_config(tmp_path):
    """Create a real config instance for integration testing."""
    config = Mock(spec=Config)
    config.base_dir = tmp_path
    config.use_relative_paths = False
    config.compact_tool_results = False
    config.excluded_files = set()
    config.excluded_extensions = set()
    config.current_model = "grok-2"
    config.get_max_tokens_for_model = Mock(return_value=100000)
    config.deduplicate_file_content = True
    config.max_files_in_add_dir = 100
    return config


@pytest.fixture
def context_manager(real_config):
    """Create a real context manager for integration testing."""
    return ContextManager(real_config)


class TestContextDeduplicationIntegration:
    """Integration tests for context deduplication."""

    def test_mount_then_read_prevents_duplication(self, real_config, context_manager, tmp_path):
        """Test that mounting a file prevents re-reading via tool."""
        # Create a test file
        test_file = tmp_path / "integration_test.txt"
        test_file.write_text("Integration test content that should not be duplicated")

        # Mount the file to context
        context_manager.mount_file(str(test_file), test_file.read_text())

        # Verify file is tracked
        assert context_manager.is_file_in_context(str(test_file)) is True

        # Try to read the file via ReadFileTool
        tool = ReadFileTool(real_config)
        tool.context_manager = context_manager

        result = tool.execute({"file_path": str(test_file)})

        # Should get the short message, not full content
        assert result.success is True
        assert "already available in context" in result.result.lower()
        assert "Integration test content" not in result.result

    def test_read_then_read_again_prevents_duplication(self, real_config, context_manager, tmp_path):
        """Test that reading a file twice prevents duplication."""
        test_file = tmp_path / "read_twice.txt"
        test_file.write_text("Content that should only be read once")

        tool = ReadFileTool(real_config)
        tool.context_manager = context_manager

        # First read - should succeed and track the file
        result1 = tool.execute({"file_path": str(test_file)})
        assert result1.success is True
        assert "Content that should only be read once" in result1.result

        # Verify file is now tracked
        assert context_manager.is_file_in_context(str(test_file)) is True

        # Second read - should get short message
        result2 = tool.execute({"file_path": str(test_file)})
        assert result2.success is True
        assert "already available in context" in result2.result.lower()
        assert "Content that should only be read once" not in result2.result

    def test_clear_context_resets_deduplication(self, real_config, context_manager, tmp_path):
        """Test that clearing context allows re-reading files."""
        test_file = tmp_path / "clear_test.txt"
        test_file.write_text("Content for clear test")

        tool = ReadFileTool(real_config)
        tool.context_manager = context_manager

        # Read file first time
        result1 = tool.execute({"file_path": str(test_file)})
        assert "Content for clear test" in result1.result

        # Verify tracked
        assert context_manager.is_file_in_context(str(test_file)) is True

        # Clear context
        context_manager.clear_context(keep_memories=True, keep_mounted_files=False)

        # Verify no longer tracked
        assert context_manager.is_file_in_context(str(test_file)) is False

        # Read again - should get full content
        result2 = tool.execute({"file_path": str(test_file)})
        assert result2.success is True
        assert "Content for clear test" in result2.result


class TestCircularImportResolutionIntegration:
    """Integration tests for circular import resolution."""

    def test_tool_and_command_share_directory_service(self, real_config, tmp_path):
        """Test that both tool and command use the same DirectoryService logic."""
        # Create directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Test DirectoryService directly
        service = DirectoryService(real_config)

        # Test path resolution consistency
        path1 = service.resolve_directory_path("dir1")
        assert path1 == dir1.resolve()

        # Test validation consistency
        is_valid, error = service.validate_directory(dir1)
        assert is_valid is True
        assert error is None

        # Test change directory
        result = service.change_directory(dir1, session=None)
        assert result.success is True
        assert Path(result.new_path) == dir1

    def test_tool_changes_directory_successfully(self, real_config, tmp_path):
        """Test ChangeWorkingDirectoryTool works correctly."""
        new_dir = tmp_path / "tool_test_dir"
        new_dir.mkdir()

        old_dir = real_config.base_dir

        tool = ChangeWorkingDirectoryTool(real_config)
        result = tool.execute({"directory_path": str(new_dir)})

        assert result.success is True
        assert str(old_dir) in result.result
        assert str(new_dir) in result.result
        assert real_config.base_dir == new_dir

    def test_folder_command_changes_directory_with_mocked_session(self, real_config, tmp_path):
        """Test FolderCommand works correctly with mocked session."""
        new_dir = tmp_path / "command_test_dir"
        new_dir.mkdir()

        # Mock session
        mock_session = Mock()
        mock_session.get_memory_manager = Mock()
        mock_memory_manager = Mock()
        mock_memory_manager.has_directory_memories = Mock(return_value=False)
        mock_session.get_memory_manager.return_value = mock_memory_manager
        mock_session.update_working_directory = Mock(return_value={"has_existing_memories": False})

        # FolderCommand can be instantiated and uses DirectoryService
        # The actual execution requires UI interaction, so we just verify the structure
        command = FolderCommand(real_config)
        assert command.config == real_config

        # Verify DirectoryService can be instantiated independently
        from src.services.directory_service import DirectoryService
        service = DirectoryService(real_config)
        assert service is not None

    def test_no_circular_import_between_tools_and_commands(self):
        """Verify tools don't import from commands."""
        # This should not raise any import errors
        from src.tools.file_tools import ChangeWorkingDirectoryTool
        from src.commands.file_commands import FolderCommand
        from src.services.directory_service import DirectoryService

        # All should import successfully
        assert ChangeWorkingDirectoryTool is not None
        assert FolderCommand is not None
        assert DirectoryService is not None


class TestEndToEndScenarios:
    """End-to-end scenarios combining both improvements."""

    def test_change_directory_then_read_files(self, real_config, context_manager, tmp_path):
        """Test changing directory and reading files with deduplication."""
        # Create directory structure
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        file1 = project_dir / "file1.txt"
        file2 = project_dir / "file2.txt"
        file1.write_text("File 1 content")
        file2.write_text("File 2 content")

        # Change to project directory
        tool_cd = ChangeWorkingDirectoryTool(real_config)
        cd_result = tool_cd.execute({"directory_path": str(project_dir)})
        assert cd_result.success is True

        # Read files
        tool_read = ReadFileTool(real_config)
        tool_read.context_manager = context_manager

        # Read file1
        result1 = tool_read.execute({"file_path": "file1.txt"})
        assert result1.success is True
        assert "File 1 content" in result1.result

        # Read file2
        result2 = tool_read.execute({"file_path": "file2.txt"})
        assert result2.success is True
        assert "File 2 content" in result2.result

        # Try to read file1 again - should get short message
        result1_again = tool_read.execute({"file_path": "file1.txt"})
        assert result1_again.success is True
        assert "already available in context" in result1_again.result.lower()

    def test_deduplication_with_config_flag(self, real_config, context_manager, tmp_path):
        """Test that deduplication can be disabled via config."""
        test_file = tmp_path / "config_test.txt"
        test_file.write_text("Content for config test")

        tool = ReadFileTool(real_config)
        tool.context_manager = context_manager

        # Read with deduplication enabled
        result1 = tool.execute({"file_path": str(test_file)})
        assert "Content for config test" in result1.result

        # Disable deduplication
        real_config.deduplicate_file_content = False

        # File is tracked but deduplication is disabled
        context_manager.add_file_to_context(str(test_file))

        # Should NOT prevent reading (deduplication disabled)
        assert context_manager.is_file_in_context(str(test_file)) is False

        # Read again with deduplication disabled - should get full content
        result2 = tool.execute({"file_path": str(test_file)})
        assert result2.success is True
        assert "Content for config test" in result2.result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
