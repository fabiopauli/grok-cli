#!/usr/bin/env python3

"""
Editor Utilities - Deterministic search and replace

Provides indentation-aware, exact-match search and replace functionality.
"""

from typing import Tuple


def normalize_indentation(text: str) -> str:
    """
    Normalize indentation in text by converting to consistent spaces.

    This helps match code blocks even if indentation whitespace differs.
    Converts tabs to 4 spaces and normalizes multiple spaces.

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Convert tabs to spaces
    normalized = text.replace("\t", "    ")
    return normalized


def find_match_with_normalized_indent(content: str, search_block: str) -> Tuple[int, int, int]:
    """
    Find search_block in content, normalizing indentation for matching.

    Args:
        content: Full file content
        search_block: Block to search for

    Returns:
        Tuple of (match_count, start_index, end_index)
        If match_count != 1, start_index and end_index are -1
    """
    # Normalize both content and search block
    normalized_content = normalize_indentation(content)
    normalized_search = normalize_indentation(search_block.strip())

    # Find all occurrences
    matches = []
    start = 0

    while True:
        index = normalized_content.find(normalized_search, start)
        if index == -1:
            break

        matches.append((index, index + len(normalized_search)))
        start = index + 1

    match_count = len(matches)

    if match_count == 1:
        # Map back to original content positions
        # Since we only normalized whitespace, the positions should be close
        start_idx, end_idx = matches[0]
        return (match_count, start_idx, end_idx)
    else:
        return (match_count, -1, -1)


def search_and_replace(
    content: str, search_block: str, replace_block: str, strict: bool = True
) -> Tuple[bool, str, int, str]:
    """
    Perform deterministic search and replace with indentation awareness.

    Args:
        content: Full file content
        search_block: Block to search for
        replace_block: Replacement block
        strict: If True, fail if match count != 1 (default: True)

    Returns:
        Tuple of (success, new_content, match_count, error_msg)
        - success: True if replacement succeeded
        - new_content: Modified content (or original if failed)
        - match_count: Number of matches found
        - error_msg: Error message if failed, empty string if succeeded
    """
    # Strip leading/trailing whitespace from search block
    search_block = search_block.strip()

    if not search_block:
        return (False, content, 0, "Search block cannot be empty")

    # Find match with normalized indentation
    match_count, start_idx, end_idx = find_match_with_normalized_indent(
        content, search_block
    )

    # Check match count
    if match_count == 0:
        return (
            False,
            content,
            0,
            f"Search block not found in file. Make sure you're searching for an exact code snippet that exists in the file.",
        )

    if strict and match_count > 1:
        return (
            False,
            content,
            match_count,
            f"Found {match_count} matches for search block. Please provide more context to make the search unique. "
            f"You can include more surrounding code or distinctive elements to ensure exactly 1 match.",
        )

    if not strict and match_count > 1:
        # Non-strict mode: replace all matches
        # For simplicity, use string replace on normalized content
        normalized_content = normalize_indentation(content)
        normalized_search = normalize_indentation(search_block)
        new_content = normalized_content.replace(normalized_search, replace_block.strip())
        return (True, new_content, match_count, "")

    # Single match - perform replacement
    # Preserve the original indentation of the match location
    matched_original = content[start_idx:end_idx]
    leading_whitespace = matched_original[: len(matched_original) - len(matched_original.lstrip())]

    # Apply leading whitespace to replacement block
    replace_lines = replace_block.strip().split("\n")
    indented_replace = "\n".join(leading_whitespace + line for line in replace_lines)

    # Perform replacement
    new_content = content[:start_idx] + indented_replace + content[end_idx:]

    return (True, new_content, 1, "")


def validate_replacement(
    original_content: str, new_content: str, search_block: str, replace_block: str
) -> Tuple[bool, str]:
    """
    Validate that a replacement was successful.

    Args:
        original_content: Original file content
        new_content: New file content after replacement
        search_block: Block that was searched for
        replace_block: Replacement block

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check that content actually changed
    if original_content == new_content:
        return (False, "Replacement did not modify the content")

    # Check that search block no longer exists
    normalized_new = normalize_indentation(new_content)
    normalized_search = normalize_indentation(search_block.strip())

    if normalized_search in normalized_new:
        return (
            False,
            "Search block still found in content after replacement. This shouldn't happen.",
        )

    # Check that replace block now exists
    normalized_replace = normalize_indentation(replace_block.strip())

    if normalized_replace not in normalized_new:
        return (
            False,
            "Replace block not found in content after replacement. Check indentation and formatting.",
        )

    return (True, "")
