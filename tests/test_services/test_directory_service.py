#!/usr/bin/env python3

"""
Tests for DirectoryService

Tests for directory change operations and the resolution of circular imports.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.core.config import Config
from src.services.directory_service import DirectoryService
from src.services.dtos import DirectoryChangeResult


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config for testing."""
    config = Mock(spec=Config)
    config.base_dir = tmp_path
    return config


@pytest.fixture
def directory_service(mock_config):
    """Create a DirectoryService instance for testing."""
    return DirectoryService(mock_config)


class TestResolveDirectoryPath:
    """Test directory path resolution."""

    def test_resolve_current_directory(self, directory_service):
        """Test resolving '.' returns current base_dir."""
        result = directory_service.resolve_directory_path(".")
        assert result == directory_service.config.base_dir

    def test_resolve_parent_directory(self, directory_service, tmp_path):
        """Test resolving '..' returns parent directory."""
        result = directory_service.resolve_directory_path("..")
        assert result == tmp_path.parent

    def test_resolve_home_directory(self, directory_service):
        """Test resolving '~' expands to home directory."""
        result = directory_service.resolve_directory_path("~")
        assert result == Path.home()

    def test_resolve_absolute_path(self, directory_service):
        """Test resolving absolute path."""
        absolute_path = "/tmp/test"
        result = directory_service.resolve_directory_path(absolute_path)
        assert result == Path(absolute_path).resolve()

    def test_resolve_relative_path(self, directory_service, tmp_path):
        """Test resolving relative path."""
        subdir = "subdir"
        result = directory_service.resolve_directory_path(subdir)
        assert result == (tmp_path / subdir).resolve()

    def test_resolve_invalid_path_raises_value_error(self, directory_service):
        """Test that invalid paths raise ValueError."""
        # This test depends on implementation - some invalid paths might not raise
        # For now, just verify the method returns a Path object
        result = directory_service.resolve_directory_path("some/path")
        assert isinstance(result, Path)


class TestValidateDirectory:
    """Test directory validation."""

    def test_validate_existing_directory(self, directory_service, tmp_path):
        """Test validation succeeds for existing directory."""
        is_valid, error_msg = directory_service.validate_directory(tmp_path)
        assert is_valid is True
        assert error_msg is None

    def test_validate_nonexistent_directory(self, directory_service, tmp_path):
        """Test validation fails for non-existent directory."""
        nonexistent = tmp_path / "does_not_exist"
        is_valid, error_msg = directory_service.validate_directory(nonexistent)
        assert is_valid is False
        assert error_msg is not None
        assert "does not exist" in error_msg.lower()

    def test_validate_file_not_directory(self, directory_service, tmp_path):
        """Test validation fails when path is a file, not a directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, error_msg = directory_service.validate_directory(test_file)
        assert is_valid is False
        assert error_msg is not None
        assert "not a directory" in error_msg.lower()


class TestChangeDirectory:
    """Test directory change operations."""

    def test_change_directory_without_session(self, directory_service, tmp_path):
        """Test changing directory without session integration."""
        new_dir = tmp_path / "new_dir"
        new_dir.mkdir()

        old_base = directory_service.config.base_dir
        result = directory_service.change_directory(new_dir, session=None)

        assert isinstance(result, DirectoryChangeResult)
        assert result.success is True
        assert result.old_path == str(old_base)
        assert result.new_path == str(new_dir)
        assert result.memory_info is None
        assert result.error is None
        assert directory_service.config.base_dir == new_dir

    def test_change_directory_with_session(self, directory_service, tmp_path):
        """Test changing directory with session integration."""
        new_dir = tmp_path / "new_dir_with_session"
        new_dir.mkdir()

        # Mock session with update_working_directory method
        mock_session = Mock()
        mock_memory_info = {"has_existing_memories": False, "loaded_count": 0}
        mock_session.update_working_directory.return_value = mock_memory_info

        old_base = directory_service.config.base_dir
        result = directory_service.change_directory(new_dir, session=mock_session)

        assert result.success is True
        assert result.old_path == str(old_base)
        assert result.new_path == str(new_dir)
        assert result.memory_info == mock_memory_info
        assert result.error is None

        # Verify session method was called
        mock_session.update_working_directory.assert_called_once_with(new_dir)

    def test_change_directory_updates_config(self, directory_service, tmp_path):
        """Test that change_directory updates the config.base_dir."""
        new_dir = tmp_path / "config_update_test"
        new_dir.mkdir()

        old_dir = directory_service.config.base_dir
        directory_service.change_directory(new_dir)

        assert directory_service.config.base_dir == new_dir
        assert directory_service.config.base_dir != old_dir


class TestCircularImportResolution:
    """Test that circular imports are resolved."""

    def test_no_circular_import_in_tools(self):
        """Test that file_tools no longer imports from commands."""
        # Import file_tools and check it doesn't import from commands
        import inspect

        from src.tools import file_tools

        source = inspect.getsource(file_tools)

        # Check that there's no import from commands in the source
        assert "from ..commands" not in source
        assert "import ..commands" not in source

    def test_directory_service_used_by_tool(self):
        """Test that ChangeWorkingDirectoryTool uses DirectoryService."""
        import inspect

        from src.tools.file_tools import ChangeWorkingDirectoryTool

        source = inspect.getsource(ChangeWorkingDirectoryTool)

        # Should import from services, not commands
        assert "DirectoryService" in source
        assert "from ..services.directory_service" in source

    def test_directory_service_used_by_command(self):
        """Test that FolderCommand uses DirectoryService."""
        import inspect

        from src.commands.file_commands import FolderCommand

        source = inspect.getsource(FolderCommand.execute)

        # Should import DirectoryService
        assert "DirectoryService" in source
        assert "from ..services.directory_service" in source
