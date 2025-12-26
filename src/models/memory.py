#!/usr/bin/env python3

"""
Pydantic models for memories

Provides type-safe, validated memory structures.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Memory(BaseModel):
    """
    Typed memory structure with validation.

    Replaces untyped Dict[str, Any] with validated Pydantic model.
    """

    id: str = Field(..., description="Unique memory ID (format: mem_XXXXXXXX)")
    type: Literal[
        "user_preference", "architectural_decision", "important_fact", "project_context"
    ] = Field(..., description="Type of memory")
    content: str = Field(..., description="Memory content")
    created: datetime = Field(..., description="When the memory was created")
    scope: Literal["directory", "global"] = Field(..., description="Memory scope")

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate memory ID format (mem_XXXXXXXX)."""
        if not re.match(r"^mem_[a-f0-9]{8}$", v):
            raise ValueError(
                f"Invalid memory ID format: {v}. "
                "Must match pattern: mem_XXXXXXXX (8 hex characters)"
            )
        return v

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Validate that memory content is not empty."""
        if not v or not v.strip():
            raise ValueError("Memory content cannot be empty or whitespace-only")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "mem_a1b2c3d4",
                    "type": "user_preference",
                    "content": "Always use type hints in Python code",
                    "created": "2024-01-01T00:00:00",
                    "scope": "global",
                },
                {
                    "id": "mem_e5f6g7h8",
                    "type": "architectural_decision",
                    "content": "Using FastAPI for REST API implementation",
                    "created": "2024-01-02T10:30:00",
                    "scope": "directory",
                },
            ]
        }
    }

    def to_dict(self) -> dict:
        """
        Convert to dictionary (for JSON serialization).

        Returns:
            Dictionary representation
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """
        Create Memory from dictionary.

        Args:
            data: Dictionary with memory data

        Returns:
            Validated Memory instance
        """
        return cls(**data)
