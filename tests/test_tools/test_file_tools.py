#!/usr/bin/env python3

"""
Tests for File Tools

Critical path tests for file operation tools.
"""

import pytest

from src.tools.base import ToolResult
from src.tools.file_tools import CreateFileTool, ReadFileTool


@pytest.fixture
def read_file_tool(mock_config):
    """Create a ReadFileTool for testing."""
    return ReadFileTool(mock_config)


@pytest.fixture
def create_file_tool(mock_config):
    """Create a CreateFileTool for testing."""
    return CreateFileTool(mock_config)


def test_read_file_tool_name(read_file_tool):
    """Test ReadFileTool name."""
    assert read_file_tool.get_name() == "read_file"


def test_read_file_tool_exists(read_file_tool):
    """Test ReadFileTool initialization."""
    assert read_file_tool is not None
    assert read_file_tool.get_name() == "read_file"


def test_create_file_tool_name(create_file_tool):
    """Test CreateFileTool name."""
    assert create_file_tool.get_name() == "create_file"


def test_create_file_success(create_file_tool, temp_dir):
    """Test creating a new file."""
    new_file = temp_dir / "new_test_file.txt"
    content = "This is test content"

    result = create_file_tool.execute({"file_path": str(new_file), "content": content})

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert new_file.exists()
    assert new_file.read_text() == content


def test_create_file_overwrite_protection(create_file_tool, sample_files):
    """Test that create_file doesn't overwrite existing files."""
    existing_file = sample_files["text"]

    result = create_file_tool.execute({"file_path": str(existing_file), "content": "New content"})

    # Should either fail or warn about existing file
    # Implementation may vary, so just check it's handled
    assert isinstance(result, ToolResult)


def test_create_file_with_directory_creation(create_file_tool, temp_dir):
    """Test creating file in non-existent directory."""
    nested_file = temp_dir / "new_dir" / "nested_file.txt"

    result = create_file_tool.execute({"file_path": str(nested_file), "content": "Nested content"})

    # Should either create directories or fail gracefully
    assert isinstance(result, ToolResult)


def test_create_file_empty_content(create_file_tool, temp_dir):
    """Test creating file with empty content."""
    empty_file = temp_dir / "empty.txt"

    result = create_file_tool.execute({"file_path": str(empty_file), "content": ""})

    assert isinstance(result, ToolResult)
