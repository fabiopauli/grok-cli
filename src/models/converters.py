#!/usr/bin/env python3

"""
Converters for backward compatibility

Provides conversion between legacy Dict[str, Any] and Pydantic models.
"""

from typing import Any

from .message import Message


def dict_to_message(data: dict[str, Any]) -> Message:
    """
    Convert legacy dict to Pydantic Message.

    Args:
        data: Dictionary with message data

    Returns:
        Validated Message instance

    Raises:
        ValidationError: If data doesn't match Message schema
    """
    return Message(**data)


def message_to_dict(msg: Message, exclude_none: bool = True) -> dict[str, Any]:
    """
    Convert Pydantic Message to dict for backward compatibility.

    Args:
        msg: Message instance
        exclude_none: Whether to exclude None values from output

    Returns:
        Dictionary representation of message
    """
    return msg.model_dump(exclude_none=exclude_none)


def dict_list_to_messages(data_list: list[dict[str, Any]]) -> list[Message]:
    """
    Convert list of dicts to list of Messages.

    Args:
        data_list: List of message dictionaries

    Returns:
        List of validated Message instances
    """
    return [dict_to_message(data) for data in data_list]


def messages_to_dict_list(
    messages: list[Message], exclude_none: bool = True
) -> list[dict[str, Any]]:
    """
    Convert list of Messages to list of dicts.

    Args:
        messages: List of Message instances
        exclude_none: Whether to exclude None values

    Returns:
        List of message dictionaries
    """
    return [message_to_dict(msg, exclude_none=exclude_none) for msg in messages]
