#!/usr/bin/env python3

"""
Tests for MemoryService

Critical path tests for memory service business logic.
"""


def test_save_memory_success(memory_service):
    """Test successful memory save."""
    result = memory_service.save_memory(
        content="Test memory content", memory_type="user_preference", scope="global"
    )

    assert result.success is True
    assert result.memory_id is not None
    assert result.memory_id.startswith("mem_")
    assert len(result.memory_id) == 12  # "mem_" + 8 hex chars


def test_list_all_memories_empty(memory_service):
    """Test listing memories when none exist."""
    result = memory_service.list_all_memories()

    assert result.total_count == 0
    assert result.scope == "all"
    assert result.memories == []


def test_list_all_memories_with_data(memory_service):
    """Test listing all memories after saving some."""
    # Save some memories
    memory_service.save_memory("Test 1", "user_preference", "global")
    memory_service.save_memory("Test 2", "important_fact", "directory")
    memory_service.save_memory("Test 3", "architectural_decision", "global")

    # List all
    result = memory_service.list_all_memories()

    assert result.total_count == 3
    assert result.scope == "all"
    assert len(result.memories) == 3


def test_list_global_memories(memory_service):
    """Test listing only global memories."""
    # Save mixed scope memories
    memory_service.save_memory("Global 1", "user_preference", "global")
    memory_service.save_memory("Directory 1", "important_fact", "directory")
    memory_service.save_memory("Global 2", "architectural_decision", "global")

    # List global only
    result = memory_service.list_global_memories()

    assert result.total_count == 2
    assert result.scope == "global"
    assert all(m["scope"] == "global" for m in result.memories)


def test_list_directory_memories(memory_service):
    """Test listing only directory memories."""
    # Save mixed scope memories
    memory_service.save_memory("Global 1", "user_preference", "global")
    memory_service.save_memory("Directory 1", "important_fact", "directory")
    memory_service.save_memory("Directory 2", "project_context", "directory")

    # List directory only
    result = memory_service.list_directory_memories()

    assert result.total_count == 2
    assert result.scope == "directory"
    assert all(m["scope"] == "directory" for m in result.memories)


def test_remove_memory_success(memory_service):
    """Test removing an existing memory."""
    # Save a memory
    save_result = memory_service.save_memory("Test memory", "user_preference", "global")
    memory_id = save_result.memory_id

    # Remove it
    remove_result = memory_service.remove_memory(memory_id)

    assert remove_result.success is True
    assert remove_result.found is True
    assert remove_result.memory_id == memory_id

    # Verify it's gone
    list_result = memory_service.list_all_memories()
    assert list_result.total_count == 0


def test_remove_memory_not_found(memory_service):
    """Test removing a non-existent memory."""
    result = memory_service.remove_memory("mem_nonexist")

    assert result.success is False
    assert result.found is False


def test_clear_directory_memories(memory_service):
    """Test clearing directory memories."""
    # Save mixed memories
    memory_service.save_memory("Global 1", "user_preference", "global")
    memory_service.save_memory("Directory 1", "important_fact", "directory")
    memory_service.save_memory("Directory 2", "project_context", "directory")

    # Clear directory memories
    result = memory_service.clear_directory_memories()

    assert result.cleared_count == 2
    assert result.scope == "directory"

    # Verify global memories remain
    list_result = memory_service.list_all_memories()
    assert list_result.total_count == 1
    assert list_result.memories[0]["scope"] == "global"


def test_clear_global_memories(memory_service):
    """Test clearing global memories."""
    # Save mixed memories
    memory_service.save_memory("Global 1", "user_preference", "global")
    memory_service.save_memory("Global 2", "architectural_decision", "global")
    memory_service.save_memory("Directory 1", "important_fact", "directory")

    # Clear global memories
    result = memory_service.clear_global_memories()

    assert result.cleared_count == 2
    assert result.scope == "global"

    # Verify directory memories remain
    list_result = memory_service.list_all_memories()
    assert list_result.total_count == 1
    assert list_result.memories[0]["scope"] == "directory"


def test_clear_all_memories(memory_service):
    """Test clearing all memories."""
    # Save mixed memories
    memory_service.save_memory("Global 1", "user_preference", "global")
    memory_service.save_memory("Directory 1", "important_fact", "directory")

    # Clear all
    result = memory_service.clear_all_memories()

    assert result.cleared_count == 2
    assert result.scope == "all"

    # Verify all gone
    list_result = memory_service.list_all_memories()
    assert list_result.total_count == 0


def test_get_statistics(memory_service):
    """Test getting memory statistics."""
    # Save some memories
    memory_service.save_memory("Global", "user_preference", "global")
    memory_service.save_memory("Directory", "important_fact", "directory")

    # Get stats
    stats = memory_service.get_statistics()

    assert "total_memories" in stats
    assert "global_memories" in stats
    assert "current_directory_memories" in stats
    assert stats["total_memories"] == 2
    assert stats["global_memories"] == 1
