#!/usr/bin/env python3

"""
Tests for Stale Mount Problem Fix

This test suite validates the fix for the "stale mount" problem where
mounted files become outdated after being edited on disk.

Test Coverage:
1. File editing refreshes mounted file content
2. File creation/overwrite refreshes mounted file content
3. Multiple file operations maintain fresh content
4. Error handling when file is deleted after mounting
5. Integration with EditFileTool and CreateFileTool
"""

import pytest
from pathlib import Path

from src.core.config import Config
from src.core.context_manager import ContextManager
from src.tools.file_tools import EditFileTool, CreateFileTool, CreateMultipleFilesTool


class TestStaleMountProblemFix:
    """Test suite for stale mount problem fix."""

    def test_mount_file_stores_content_in_memory(self, mock_config, temp_dir):
        """Verify that mounting a file caches its content in memory."""
        # Create a test file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        # Mount the file
        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Verify file is mounted with correct content
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert normalized_path in mounted_files
        assert mounted_files[normalized_path].content == initial_content

    def test_refresh_mounted_file_updates_content(self, mock_config, temp_dir):
        """Verify that refresh_mounted_file_if_exists updates cached content."""
        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Modify the file on disk
        new_content = "def hello():\n    print('Hello, World!')\n"
        test_file.write_text(new_content)

        # Refresh the mounted file
        result = context_manager.refresh_mounted_file_if_exists(str(test_file))

        # Verify refresh succeeded
        assert result is True

        # Verify mounted content is updated
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert mounted_files[normalized_path].content == new_content

    def test_refresh_nonexistent_mount_returns_false(self, mock_config, temp_dir):
        """Verify that refreshing a non-mounted file returns False."""
        test_file = temp_dir / "not_mounted.py"
        test_file.write_text("content")

        context_manager = ContextManager(mock_config)

        # Try to refresh a file that isn't mounted
        result = context_manager.refresh_mounted_file_if_exists(str(test_file))

        assert result is False

    def test_refresh_deleted_file_unmounts_it(self, mock_config, temp_dir):
        """Verify that refreshing a deleted file unmounts it gracefully."""
        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Delete the file from disk
        test_file.unlink()

        # Try to refresh - should unmount the file
        result = context_manager.refresh_mounted_file_if_exists(str(test_file))

        # Verify refresh failed
        assert result is False

        # Verify file was unmounted
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert normalized_path not in mounted_files

    def test_edit_file_tool_refreshes_mounted_file(self, mock_config, temp_dir):
        """Verify that EditFileTool refreshes mounted files after editing."""
        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Create EditFileTool and inject context_manager
        edit_tool = EditFileTool(mock_config)
        edit_tool.set_context_manager(context_manager)

        # Edit the file using the tool
        new_snippet = "def hello():\n    print('Hello, World!')\n"
        result = edit_tool.execute({
            "file_path": str(test_file),
            "original_snippet": initial_content,
            "new_snippet": new_snippet
        })

        # Verify edit succeeded
        assert result.success is True

        # Verify mounted content was refreshed
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert mounted_files[normalized_path].content == new_snippet

    def test_create_file_tool_refreshes_if_mounted(self, mock_config, temp_dir):
        """Verify that CreateFileTool refreshes mounted files when overwriting."""
        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Create CreateFileTool and inject context_manager
        create_tool = CreateFileTool(mock_config)
        create_tool.set_context_manager(context_manager)

        # Overwrite the file using the tool
        new_content = "def goodbye():\n    print('Goodbye!')\n"
        result = create_tool.execute({
            "file_path": str(test_file),
            "content": new_content
        })

        # Verify creation succeeded
        assert result.success is True

        # Verify mounted content was refreshed
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert mounted_files[normalized_path].content == new_content

    def test_create_multiple_files_refreshes_mounted_files(self, mock_config, temp_dir):
        """Verify that CreateMultipleFilesTool refreshes mounted files."""
        # Create and mount multiple files
        file1 = temp_dir / "file1.py"
        file2 = temp_dir / "file2.py"

        initial_content1 = "# File 1\n"
        initial_content2 = "# File 2\n"

        file1.write_text(initial_content1)
        file2.write_text(initial_content2)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(file1), initial_content1)
        context_manager.mount_file(str(file2), initial_content2)

        # Create tool and inject context_manager
        create_multi_tool = CreateMultipleFilesTool(mock_config)
        create_multi_tool.set_context_manager(context_manager)

        # Overwrite both files
        new_content1 = "# File 1 - Updated\n"
        new_content2 = "# File 2 - Updated\n"

        result = create_multi_tool.execute({
            "files": [
                {"path": str(file1), "content": new_content1},
                {"path": str(file2), "content": new_content2}
            ]
        })

        # Verify creation succeeded
        assert result.success is True

        # Verify both mounted files were refreshed
        mounted_files = context_manager.get_mounted_files()
        normalized_path1 = str(file1.resolve())
        normalized_path2 = str(file2.resolve())

        assert mounted_files[normalized_path1].content == new_content1
        assert mounted_files[normalized_path2].content == new_content2

    def test_token_count_updates_on_refresh(self, mock_config, temp_dir):
        """Verify that token count is recalculated when refreshing."""
        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "short"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Get initial token count
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        initial_token_count = mounted_files[normalized_path].token_count

        # Modify file with much longer content
        new_content = "This is a much longer piece of text " * 50
        test_file.write_text(new_content)

        # Refresh the mounted file
        context_manager.refresh_mounted_file_if_exists(str(test_file))

        # Verify token count increased
        mounted_files = context_manager.get_mounted_files()
        new_token_count = mounted_files[normalized_path].token_count
        assert new_token_count > initial_token_count

    def test_timestamp_updates_on_refresh(self, mock_config, temp_dir):
        """Verify that timestamp is updated when refreshing."""
        import time

        # Create and mount a file
        test_file = temp_dir / "test.py"
        initial_content = "def hello():\n    print('Hello')\n"
        test_file.write_text(initial_content)

        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), initial_content)

        # Get initial timestamp
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        initial_timestamp = mounted_files[normalized_path].timestamp

        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)

        # Modify and refresh
        new_content = "def hello():\n    print('Hello, World!')\n"
        test_file.write_text(new_content)
        context_manager.refresh_mounted_file_if_exists(str(test_file))

        # Verify timestamp was updated
        mounted_files = context_manager.get_mounted_files()
        new_timestamp = mounted_files[normalized_path].timestamp
        assert new_timestamp > initial_timestamp

    def test_regression_prevention_scenario(self, mock_config, temp_dir):
        """
        Test the full regression loop prevention scenario:
        1. Mount file with bug
        2. AI edits file to fix bug
        3. Verify mounted content reflects the fix (not stale)
        """
        # Create a file with a "bug"
        test_file = temp_dir / "buggy.py"
        buggy_content = "def add(a, b):\n    return a - b  # BUG: should be +\n"
        test_file.write_text(buggy_content)

        # Mount the file (AI reads it)
        context_manager = ContextManager(mock_config)
        context_manager.mount_file(str(test_file), buggy_content)

        # Verify AI sees the bug
        mounted_files = context_manager.get_mounted_files()
        normalized_path = str(test_file.resolve())
        assert "return a - b" in mounted_files[normalized_path].content

        # AI edits the file to fix the bug
        edit_tool = EditFileTool(mock_config)
        edit_tool.set_context_manager(context_manager)

        fixed_content = "def add(a, b):\n    return a + b  # FIXED\n"
        edit_tool.execute({
            "file_path": str(test_file),
            "original_snippet": buggy_content,
            "new_snippet": fixed_content
        })

        # Verify mounted content now shows the fix (not stale bug)
        mounted_files = context_manager.get_mounted_files()
        assert "return a + b" in mounted_files[normalized_path].content
        assert "return a - b" not in mounted_files[normalized_path].content

        # This prevents the regression loop where AI would see the old bug
        # and try to fix it again


class TestToolContextManagerInjection:
    """Test that tools can receive context_manager via dependency injection."""

    def test_base_tool_has_set_context_manager_method(self, mock_config):
        """Verify BaseTool has set_context_manager method."""
        from src.tools.base import BaseTool

        # Create a concrete tool instance
        edit_tool = EditFileTool(mock_config)

        # Verify it has the method
        assert hasattr(edit_tool, 'set_context_manager')
        assert callable(edit_tool.set_context_manager)

    def test_set_context_manager_stores_reference(self, mock_config):
        """Verify set_context_manager stores the context_manager reference."""
        context_manager = ContextManager(mock_config)
        edit_tool = EditFileTool(mock_config)

        # Initially should be None
        assert edit_tool.context_manager is None

        # Set context_manager
        edit_tool.set_context_manager(context_manager)

        # Should now have reference
        assert edit_tool.context_manager is context_manager

    def test_tools_work_without_context_manager(self, mock_config, temp_dir):
        """Verify tools still work if context_manager is not set."""
        # Create a file
        test_file = temp_dir / "test.py"
        test_file.write_text("old content")

        # Create tool without context_manager
        edit_tool = EditFileTool(mock_config)
        assert edit_tool.context_manager is None

        # Should still work (just won't refresh mounts)
        result = edit_tool.execute({
            "file_path": str(test_file),
            "original_snippet": "old content",
            "new_snippet": "new content"
        })

        assert result.success is True
        assert test_file.read_text() == "new content"


class TestToolExecutorInjection:
    """Test ToolExecutor's inject_context_manager method."""

    def test_tool_executor_inject_context_manager(self, mock_config):
        """Verify ToolExecutor can inject context_manager into all tools."""
        from src.tools.base import ToolExecutor

        # Create executor and register file tools
        executor = ToolExecutor(mock_config)

        edit_tool = EditFileTool(mock_config)
        create_tool = CreateFileTool(mock_config)

        executor.register_tool(edit_tool)
        executor.register_tool(create_tool)

        # Verify tools don't have context_manager yet
        assert edit_tool.context_manager is None
        assert create_tool.context_manager is None

        # Inject context_manager
        context_manager = ContextManager(mock_config)
        executor.inject_context_manager(context_manager)

        # Verify all tools now have context_manager
        assert edit_tool.context_manager is context_manager
        assert create_tool.context_manager is context_manager

    def test_inject_does_not_raise_error_for_any_tool(self, mock_config):
        """Verify inject_context_manager doesn't raise errors for any tool type."""
        from src.tools.base import ToolExecutor, BaseTool, ToolResult

        # Create a tool that inherits from BaseTool
        class MinimalTool(BaseTool):
            def get_name(self):
                return "minimal"

            def execute(self, args):
                return ToolResult.ok("success")

        executor = ToolExecutor(mock_config)
        minimal_tool = MinimalTool(mock_config)
        executor.register_tool(minimal_tool)

        # Should not raise error when injecting
        context_manager = ContextManager(mock_config)
        executor.inject_context_manager(context_manager)

        # All tools inheriting from BaseTool will have context_manager attribute
        # since it's set in BaseTool.__init__
        assert hasattr(minimal_tool, 'context_manager')
        assert minimal_tool.context_manager is context_manager
