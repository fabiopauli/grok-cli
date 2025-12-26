#!/usr/bin/env python3

"""
Pydantic models for messages

Provides type-safe, validated message structures replacing Dict[str, Any].
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ToolCall(BaseModel):
    """Represents a tool call within a message."""

    name: str = Field(..., description="Name of the tool being called")
    arguments: dict[str, Any] = Field(..., description="Arguments for the tool call")
    tool_call_id: str | None = Field(None, description="Unique ID for this tool call")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "read_file",
                "arguments": {"file_path": "/path/to/file.py"},
                "tool_call_id": "call_abc123",
            }
        }
    }


class Message(BaseModel):
    """
    Typed message structure with validation.

    Replaces untyped Dict[str, Any] with validated Pydantic model.
    """

    role: Literal["user", "assistant", "system", "tool"] = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tool_calls: list[ToolCall] | None = Field(None, description="Tool calls made by assistant")
    tool_name: str | None = Field(None, description="Name of tool for tool messages")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the message was created"
    )

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Validate that content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty or whitespace-only")
        return v

    @field_validator("tool_calls")
    @classmethod
    def validate_tool_calls(cls, v: list[ToolCall] | None, info) -> list[ToolCall] | None:
        """Validate tool calls are only present for assistant messages."""
        if v is not None and info.data.get("role") != "assistant":
            raise ValueError("Tool calls can only be present in assistant messages")
        return v

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str | None, info) -> str | None:
        """Validate tool_name is only present for tool messages."""
        if v is not None and info.data.get("role") != "tool":
            raise ValueError("tool_name can only be present in tool messages")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"role": "user", "content": "Hello, world!", "timestamp": "2024-01-01T00:00:00"},
                {
                    "role": "assistant",
                    "content": "Hello! How can I help?",
                    "tool_calls": [{"name": "read_file", "arguments": {"file_path": "test.py"}}],
                },
            ]
        }
    }
