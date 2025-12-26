#!/usr/bin/env python3

"""
Tests for Message Pydantic model

Critical path tests for message validation and conversion.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models import Message, ToolCall
from src.models.converters import dict_to_message, message_to_dict


def test_create_valid_user_message():
    """Test creating a valid user message."""
    msg = Message(role="user", content="Hello, world!")

    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    assert msg.tool_calls is None
    assert msg.tool_name is None
    assert isinstance(msg.timestamp, datetime)


def test_create_valid_assistant_message():
    """Test creating a valid assistant message."""
    msg = Message(role="assistant", content="Hello! How can I help?")

    assert msg.role == "assistant"
    assert msg.content == "Hello! How can I help?"


def test_create_system_message():
    """Test creating a system message."""
    msg = Message(role="system", content="You are a helpful assistant.")

    assert msg.role == "system"
    assert msg.content == "You are a helpful assistant."


def test_create_tool_message():
    """Test creating a tool message."""
    msg = Message(role="tool", content="File read successfully", tool_name="read_file")

    assert msg.role == "tool"
    assert msg.content == "File read successfully"
    assert msg.tool_name == "read_file"


def test_empty_content_raises_error():
    """Test that empty content raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Message(role="user", content="")

    assert "Content cannot be empty" in str(exc_info.value)


def test_whitespace_only_content_raises_error():
    """Test that whitespace-only content raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Message(role="user", content="   \n\t  ")

    assert "Content cannot be empty" in str(exc_info.value)


def test_invalid_role_raises_error():
    """Test that invalid role raises validation error."""
    with pytest.raises(ValidationError):
        Message(role="invalid_role", content="Test content")


def test_assistant_with_tool_calls():
    """Test assistant message with tool calls."""
    tool_call = ToolCall(
        name="read_file", arguments={"file_path": "/path/to/file.py"}, tool_call_id="call_123"
    )

    msg = Message(role="assistant", content="Let me read that file.", tool_calls=[tool_call])

    assert msg.role == "assistant"
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "read_file"
    assert msg.tool_calls[0].arguments["file_path"] == "/path/to/file.py"


def test_user_with_tool_calls_raises_error():
    """Test that tool calls on user message raises error."""
    tool_call = ToolCall(name="test_tool", arguments={})

    with pytest.raises(ValidationError) as exc_info:
        Message(role="user", content="Test", tool_calls=[tool_call])

    assert "Tool calls can only be present in assistant messages" in str(exc_info.value)


def test_user_with_tool_name_raises_error():
    """Test that tool_name on non-tool message raises error."""
    with pytest.raises(ValidationError) as exc_info:
        Message(role="user", content="Test", tool_name="some_tool")

    assert "tool_name can only be present in tool messages" in str(exc_info.value)


def test_dict_to_message_conversion():
    """Test converting dict to Message."""
    data = {"role": "user", "content": "Hello, world!"}

    msg = dict_to_message(data)

    assert isinstance(msg, Message)
    assert msg.role == "user"
    assert msg.content == "Hello, world!"


def test_message_to_dict_conversion():
    """Test converting Message to dict."""
    msg = Message(role="user", content="Test message")
    data = message_to_dict(msg)

    assert isinstance(data, dict)
    assert data["role"] == "user"
    assert data["content"] == "Test message"
    assert "timestamp" in data


def test_message_to_dict_exclude_none():
    """Test converting Message to dict excluding None values."""
    msg = Message(role="user", content="Test")
    data = message_to_dict(msg, exclude_none=True)

    assert "role" in data
    assert "content" in data
    # None fields should be excluded
    assert "tool_calls" not in data
    assert "tool_name" not in data


def test_round_trip_conversion():
    """Test converting Message to dict and back."""
    original = Message(
        role="assistant",
        content="Hello!",
        tool_calls=[ToolCall(name="test_tool", arguments={"key": "value"})],
    )

    # Convert to dict
    data = message_to_dict(original, exclude_none=False)

    # Convert back to Message
    restored = dict_to_message(data)

    assert restored.role == original.role
    assert restored.content == original.content
    assert len(restored.tool_calls) == len(original.tool_calls)
    assert restored.tool_calls[0].name == original.tool_calls[0].name


def test_tool_call_creation():
    """Test creating a ToolCall."""
    tool_call = ToolCall(
        name="read_file",
        arguments={"file_path": "/test.py", "encoding": "utf-8"},
        tool_call_id="call_abc123",
    )

    assert tool_call.name == "read_file"
    assert tool_call.arguments["file_path"] == "/test.py"
    assert tool_call.arguments["encoding"] == "utf-8"
    assert tool_call.tool_call_id == "call_abc123"


def test_tool_call_without_id():
    """Test creating a ToolCall without tool_call_id."""
    tool_call = ToolCall(name="test_tool", arguments={})

    assert tool_call.name == "test_tool"
    assert tool_call.arguments == {}
    assert tool_call.tool_call_id is None
