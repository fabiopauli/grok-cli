#!/usr/bin/env python3

"""
Tests for FileService

Critical path tests for file service business logic.
"""

from pathlib import Path

from src.services import FileService


def test_resolve_path_existing_file(file_service, sample_files):
    """Test resolving path to existing file."""
    python_file = sample_files["python"]

    result = file_service.resolve_path(str(python_file))

    assert result.success is True
    assert result.resolved_path is not None
    assert Path(result.resolved_path).exists()
    assert result.error is None


def test_resolve_path_nonexistent_file(file_service, temp_dir):
    """Test resolving path to non-existent file."""
    nonexistent = temp_dir / "does_not_exist.py"

    result = file_service.resolve_path(str(nonexistent))

    assert result.success is False
    assert result.resolved_path is None
    assert result.error is not None
    assert "not found" in result.error.lower() or "does not exist" in result.error.lower()


def test_resolve_path_relative(file_service, sample_files, mock_config):
    """Test resolving relative path."""
    # Create a file in base_dir
    test_file = mock_config.base_dir / "test_relative.txt"
    test_file.write_text("test content")

    result = file_service.resolve_path("test_relative.txt")

    assert result.success is True
    assert result.resolved_path is not None


def test_file_service_initialization(mock_config):
    """Test FileService initialization."""
    service = FileService(mock_config)

    assert service is not None
    assert service.config == mock_config
