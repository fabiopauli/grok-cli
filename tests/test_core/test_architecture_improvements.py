#!/usr/bin/env python3

"""
Tests for Architecture Improvements

Verifies all high and medium impact improvements from the architecture review:

High Impact:
1. Dual source of truth fix: chat_instance derived from context_manager
2. Tool schema co-location: get_schema() on BaseTool, extracted tool_schemas.py
3. main.py deduplication: handle_tool_calls delegates to tool_utils
4. Config god class extraction: tool schemas in dedicated module

Medium Impact:
5. Turn logger file tracking: regex/JSON extraction implemented
6. Structured state compression enabled by default
7. ToolResult from executor: structured success/failure instead of strings
8. Silent error swallowing replaced with logging
"""

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.config import Config
from src.core.tool_schemas import get_static_tool_schemas
from src.core.truncation_strategy import TruncationStrategy
from src.core.turn_logger import Turn, TurnEvent, TurnLogger
from src.tools.base import BaseTool, ToolExecutor, ToolResult


# ==============================================================================
# Issue #7: ToolResult structured returns (High Impact)
# ==============================================================================


class TestToolResult:
    """Test the ToolResult class and its factory methods."""

    def test_ok_creates_success_result(self):
        """Test ToolResult.ok creates a successful result."""
        result = ToolResult.ok("File read successfully")
        assert result.success is True
        assert result.result == "File read successfully"
        assert result.error is None

    def test_fail_creates_error_result(self):
        """Test ToolResult.fail creates an error result."""
        result = ToolResult.fail("File not found")
        assert result.success is False
        assert result.result == "File not found"
        assert result.error == "File not found"

    def test_constructor_direct(self):
        """Test ToolResult can be constructed directly."""
        result = ToolResult(success=True, result="ok", error=None)
        assert result.success is True
        assert result.result == "ok"


class TestToolExecutorReturnsToolResult:
    """Test that ToolExecutor.execute_tool_call returns ToolResult, not str."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.executor = ToolExecutor(self.config)

    def _make_tool_call(self, name: str, args: dict) -> dict:
        """Helper to create a tool call dict."""
        return {
            "function": {
                "name": name,
                "arguments": json.dumps(args)
            }
        }

    def test_successful_tool_returns_tool_result(self):
        """Test that a successful tool call returns a ToolResult object."""
        # Create a mock tool that returns ToolResult.ok
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "test_tool"
        mock_tool.execute.return_value = ToolResult.ok("Success!")

        self.executor.register_tool(mock_tool)
        result = self.executor.execute_tool_call(
            self._make_tool_call("test_tool", {"key": "value"})
        )

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.result == "Success!"

    def test_failed_tool_returns_tool_result(self):
        """Test that a failed tool call returns a ToolResult with success=False."""
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "failing_tool"
        mock_tool.execute.return_value = ToolResult.fail("Something went wrong")

        self.executor.register_tool(mock_tool)
        result = self.executor.execute_tool_call(
            self._make_tool_call("failing_tool", {})
        )

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Something went wrong" in result.result

    def test_unknown_tool_returns_tool_result_fail(self):
        """Test that calling an unknown tool returns ToolResult.fail."""
        result = self.executor.execute_tool_call(
            self._make_tool_call("nonexistent_tool", {})
        )

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Unknown function" in result.result

    def test_invalid_json_returns_tool_result_fail(self):
        """Test that invalid JSON arguments return ToolResult.fail."""
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "test_tool"
        self.executor.register_tool(mock_tool)

        result = self.executor.execute_tool_call({
            "function": {
                "name": "test_tool",
                "arguments": "not valid json{{"
            }
        })

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Invalid JSON" in result.result

    def test_exception_in_tool_returns_tool_result_fail(self):
        """Test that exceptions in tool execution return ToolResult.fail."""
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "error_tool"
        mock_tool.execute.side_effect = ValueError("Test error")

        self.executor.register_tool(mock_tool)
        result = self.executor.execute_tool_call(
            self._make_tool_call("error_tool", {})
        )

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Test error" in result.result


class TestTaskCompletionSignalOrdering:
    """Test that TaskCompletionSignal is caught before generic Exception."""

    def test_task_completion_signal_propagates(self):
        """Test TaskCompletionSignal is re-raised, not caught by generic handler."""
        from src.tools.lifecycle_tools import TaskCompletionSignal

        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "task_completed"
        mock_tool.execute.side_effect = TaskCompletionSignal("Done!")

        config = Config()
        executor = ToolExecutor(config)
        executor.register_tool(mock_tool)

        with pytest.raises(TaskCompletionSignal) as exc_info:
            executor.execute_tool_call({
                "function": {
                    "name": "task_completed",
                    "arguments": json.dumps({"summary": "Done!"})
                }
            })

        assert exc_info.value.summary == "Done!"


# ==============================================================================
# Issue #2: Session single source of truth (High Impact)
# ==============================================================================


class TestSessionSingleSourceOfTruth:
    """Test that GrokSession uses context_manager as the single source of truth."""

    def setup_method(self):
        """Set up test fixtures with mocked xAI client."""
        self.config = Config()
        self.config.base_dir = MagicMock(spec=True)

        # Mock the xAI client
        self.client = Mock()
        mock_chat = Mock()
        mock_chat.append = Mock()
        mock_chat.sample = Mock(return_value=Mock(content="response", tool_calls=None))
        self.client.chat.create = Mock(return_value=mock_chat)

    @patch('src.core.session.GrokSession._add_initial_context')
    @patch('src.core.session.MemoryManager')
    @patch('src.core.session.EpisodicMemoryManager')
    def test_session_has_no_chat_instance_attribute(self, mock_episodic, mock_memory, mock_init_ctx):
        """Test that GrokSession no longer stores a persistent chat_instance."""
        mock_memory_inst = Mock()
        mock_memory_inst.get_memories_for_context.return_value = ""
        mock_memory.return_value = mock_memory_inst

        mock_episodic_inst = Mock()
        mock_episodic_inst.get_episodes_for_context.return_value = []
        mock_episodic.return_value = mock_episodic_inst

        from src.core.session import GrokSession
        session = GrokSession(self.client, self.config)

        # Session should NOT have a persistent chat_instance
        assert not hasattr(session, 'chat_instance'), \
            "Session should not store a persistent chat_instance"

    @patch('src.core.session.GrokSession._add_initial_context')
    @patch('src.core.session.MemoryManager')
    @patch('src.core.session.EpisodicMemoryManager')
    def test_session_has_context_manager(self, mock_episodic, mock_memory, mock_init_ctx):
        """Test that GrokSession has a context_manager as source of truth."""
        mock_memory_inst = Mock()
        mock_memory_inst.get_memories_for_context.return_value = ""
        mock_memory.return_value = mock_memory_inst

        mock_episodic_inst = Mock()
        mock_episodic_inst.get_episodes_for_context.return_value = []
        mock_episodic.return_value = mock_episodic_inst

        from src.core.session import GrokSession
        session = GrokSession(self.client, self.config)

        assert hasattr(session, 'context_manager')
        assert session.context_manager is not None

    @patch('src.core.session.GrokSession._add_initial_context')
    @patch('src.core.session.MemoryManager')
    @patch('src.core.session.EpisodicMemoryManager')
    def test_build_chat_instance_is_derived(self, mock_episodic, mock_memory, mock_init_ctx):
        """Test that _build_chat_instance creates fresh chat from context_manager."""
        mock_memory_inst = Mock()
        mock_memory_inst.get_memories_for_context.return_value = ""
        mock_memory.return_value = mock_memory_inst

        mock_episodic_inst = Mock()
        mock_episodic_inst.get_episodes_for_context.return_value = []
        mock_episodic.return_value = mock_episodic_inst

        from src.core.session import GrokSession
        session = GrokSession(self.client, self.config)

        # Add a message through context_manager
        session.context_manager.add_system_message("Test system message")

        # Build chat instance should call client.chat.create
        chat = session._build_chat_instance("grok-3")
        self.client.chat.create.assert_called()

    @patch('src.core.session.GrokSession._add_initial_context')
    @patch('src.core.session.MemoryManager')
    @patch('src.core.session.EpisodicMemoryManager')
    def test_add_message_updates_context_manager(self, mock_episodic, mock_memory, mock_init_ctx):
        """Test that add_message routes through context_manager."""
        mock_memory_inst = Mock()
        mock_memory_inst.get_memories_for_context.return_value = ""
        mock_memory.return_value = mock_memory_inst

        mock_episodic_inst = Mock()
        mock_episodic_inst.get_episodes_for_context.return_value = []
        mock_episodic.return_value = mock_episodic_inst

        from src.core.session import GrokSession
        session = GrokSession(self.client, self.config)

        # Spy on context_manager methods
        session.context_manager.add_system_message = Mock()
        session.add_message("system", "Test message")

        session.context_manager.add_system_message.assert_called_once_with("Test message")

    @patch('src.core.session.GrokSession._add_initial_context')
    @patch('src.core.session.MemoryManager')
    @patch('src.core.session.EpisodicMemoryManager')
    def test_history_property_delegates_to_context_manager(self, mock_episodic, mock_memory, mock_init_ctx):
        """Test that the history property reads from context_manager."""
        mock_memory_inst = Mock()
        mock_memory_inst.get_memories_for_context.return_value = ""
        mock_memory.return_value = mock_memory_inst

        mock_episodic_inst = Mock()
        mock_episodic_inst.get_episodes_for_context.return_value = []
        mock_episodic.return_value = mock_episodic_inst

        from src.core.session import GrokSession
        session = GrokSession(self.client, self.config)

        session.context_manager.get_context_for_api = Mock(return_value=[{"role": "test"}])
        result = session.history

        session.context_manager.get_context_for_api.assert_called_once()
        assert result == [{"role": "test"}]


# ==============================================================================
# Issue #3/#5: Tool schema co-location and Config extraction (High Impact)
# ==============================================================================


class TestToolSchemaExtraction:
    """Test that tool schemas are properly extracted to tool_schemas.py."""

    def test_get_static_tool_schemas_returns_list(self):
        """Test that get_static_tool_schemas returns a list."""
        schemas = get_static_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) > 0

    def test_expected_tools_present(self):
        """Test that all expected tools are in the static schemas."""
        schemas = get_static_tool_schemas()
        tool_names = [s.function.name for s in schemas]

        expected_tools = [
            "read_file", "read_multiple_files",
            "create_file", "create_multiple_files",
            "edit_file", "run_bash", "run_powershell",
            "run_bash_background", "run_powershell_background",
            "check_background_job", "kill_background_job", "list_background_jobs",
            "save_memory", "change_working_directory",
            "grep_codebase", "inspect_code_structure",
            "search_replace_file", "apply_diff_patch",
            "add_task", "complete_task", "list_tasks", "remove_task",
            "create_tool", "task_completed",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, \
                f"Expected tool '{tool_name}' not found in static schemas"

    def test_config_get_tools_delegates_to_tool_schemas(self):
        """Test that Config.get_tools() includes all tools from tool_schemas."""
        config = Config()
        tools = config.get_tools()

        # Get tools from the extracted module directly
        static_schemas = get_static_tool_schemas()

        # Config.get_tools() should include at least all static schemas
        config_tool_names = {t.function.name for t in tools}
        static_tool_names = {s.function.name for s in static_schemas}

        assert static_tool_names.issubset(config_tool_names), \
            f"Missing tools: {static_tool_names - config_tool_names}"

    def test_tool_schemas_have_required_fields(self):
        """Test that all tool schemas have the required fields."""
        schemas = get_static_tool_schemas()

        for schema in schemas:
            # xai_sdk tool objects have function attribute
            assert hasattr(schema, 'function'), \
                f"Schema missing 'function' attribute"
            assert hasattr(schema.function, 'name'), \
                f"Schema function missing 'name'"
            assert hasattr(schema.function, 'description'), \
                f"Schema function missing 'description'"


class TestBaseToolGetSchema:
    """Test the get_schema() method on BaseTool for schema co-location."""

    def test_base_tool_get_schema_returns_none(self):
        """Test that BaseTool.get_schema() returns None by default."""
        config = Config()

        # Create a concrete subclass for testing
        class DummyTool(BaseTool):
            def get_name(self) -> str:
                return "dummy"

            def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult.ok("ok")

        tool = DummyTool(config)
        assert tool.get_schema() is None

    def test_subclass_can_override_get_schema(self):
        """Test that subclasses can override get_schema() to co-locate schemas."""
        config = Config()

        class CustomTool(BaseTool):
            def get_name(self) -> str:
                return "custom"

            def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult.ok("ok")

            def get_schema(self) -> dict[str, Any]:
                return {
                    "name": "custom",
                    "description": "A custom tool",
                    "parameters": {"type": "object", "properties": {}}
                }

        tool = CustomTool(config)
        schema = tool.get_schema()
        assert schema is not None
        assert schema["name"] == "custom"

    def test_tool_executor_collects_schemas(self):
        """Test that ToolExecutor.get_tool_schemas() collects schemas from tools."""
        config = Config()
        executor = ToolExecutor(config)

        # Register a tool without schema
        class NoSchemaTool(BaseTool):
            def get_name(self) -> str:
                return "no_schema"
            def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult.ok("ok")

        # Register a tool with schema
        class WithSchemaTool(BaseTool):
            def get_name(self) -> str:
                return "with_schema"
            def execute(self, args: dict[str, Any]) -> ToolResult:
                return ToolResult.ok("ok")
            def get_schema(self) -> dict[str, Any]:
                return {"name": "with_schema", "description": "Has schema"}

        executor.register_tool(NoSchemaTool(config))
        executor.register_tool(WithSchemaTool(config))

        schemas = executor.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "with_schema"


# ==============================================================================
# Issue #4: main.py handle_tool_calls deduplication (High Impact)
# ==============================================================================


class TestMainDelegation:
    """Test that main.py delegates to tool_utils.handle_tool_calls."""

    def test_tool_utils_handle_tool_calls_uses_tool_result(self):
        """Test that tool_utils.handle_tool_calls uses ToolResult.success."""
        from src.core.tool_utils import handle_tool_calls

        # Create mock response with tool calls
        mock_tool_call = Mock()
        mock_tool_call.function.name = "read_file"
        mock_tool_call.function.arguments = json.dumps({"file_path": "test.txt"})

        mock_response = Mock()
        mock_response.tool_calls = [mock_tool_call]

        # Create mock executor that returns ToolResult
        mock_executor = Mock()
        mock_executor.execute_tool_call.return_value = ToolResult.ok("File content here")

        # Create mock session
        mock_session = Mock()
        mock_session.add_message = Mock()
        mock_session.episodic_memory = Mock()
        mock_session.episodic_memory.current_episode = None

        with patch('src.core.tool_utils.get_console') as mock_get_console, \
             patch('src.core.tool_utils.display_tool_call'):
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            results = handle_tool_calls(
                mock_response, mock_executor, mock_session
            )

        # Should return results
        assert len(results) == 1
        assert results[0] == ("read_file", "File content here")

        # Session should receive the result text
        mock_session.add_message.assert_called_once_with(
            "tool", "File content here", tool_name="read_file"
        )

    def test_tool_utils_handles_failed_tool(self):
        """Test tool_utils displays warning for failed tools."""
        from src.core.tool_utils import handle_tool_calls

        mock_tool_call = Mock()
        mock_tool_call.function.name = "create_file"
        mock_tool_call.function.arguments = json.dumps({"file_path": "test.txt", "content": "x"})

        mock_response = Mock()
        mock_response.tool_calls = [mock_tool_call]

        mock_executor = Mock()
        mock_executor.execute_tool_call.return_value = ToolResult.fail("Permission denied")

        mock_session = Mock()
        mock_session.add_message = Mock()
        mock_session.episodic_memory = Mock()
        mock_session.episodic_memory.current_episode = None

        with patch('src.core.tool_utils.get_console') as mock_get_console, \
             patch('src.core.tool_utils.display_tool_call'):
            mock_console = Mock()
            mock_get_console.return_value = mock_console

            results = handle_tool_calls(
                mock_response, mock_executor, mock_session
            )

        # Should still return the result
        assert len(results) == 1

        # Console should show warning (yellow) not success (dim)
        calls = mock_console.print.call_args_list
        warning_printed = any("⚠" in str(call) for call in calls)
        assert warning_printed, "Expected warning for failed tool"


# ==============================================================================
# Issue #6: Turn logger file tracking (Medium Impact)
# ==============================================================================


class TestTurnLoggerFileTracking:
    """Test that TurnLogger properly tracks file operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config()
        self.logger = TurnLogger(self.config)

    def test_read_file_tracks_path(self):
        """Test that read_file tool results track the file path."""
        self.logger.start_turn("Read a file")
        self.logger.add_tool_response(
            "read_file",
            "Content of file '/path/to/file.py':\ndef hello(): pass"
        )

        turn = self.logger.current_turn
        assert "/path/to/file.py" in turn.files_read

    def test_create_file_tracks_path(self):
        """Test that create_file tool results track the file path."""
        self.logger.start_turn("Create a file")
        self.logger.add_tool_response(
            "create_file",
            "File created successfully: '/path/to/new_file.py'"
        )

        turn = self.logger.current_turn
        assert "/path/to/new_file.py" in turn.files_created

    def test_edit_file_tracks_path(self):
        """Test that edit_file tool results track the file path."""
        self.logger.start_turn("Edit a file")
        self.logger.add_tool_response(
            "edit_file",
            "File edited successfully: '/path/to/edited.py'"
        )

        turn = self.logger.current_turn
        assert "/path/to/edited.py" in turn.files_modified

    def test_search_replace_tracks_path(self):
        """Test that search_replace_file tool results track the file path."""
        self.logger.start_turn("Search replace")
        self.logger.add_tool_response(
            "search_replace_file",
            "Successfully replaced in '/path/to/replaced.py'"
        )

        turn = self.logger.current_turn
        assert "/path/to/replaced.py" in turn.files_modified

    def test_apply_diff_patch_tracks_path(self):
        """Test that apply_diff_patch tool results track the file path."""
        self.logger.start_turn("Apply patch")
        self.logger.add_tool_response(
            "apply_diff_patch",
            "Patch applied to '/path/to/patched.py'"
        )

        turn = self.logger.current_turn
        assert "/path/to/patched.py" in turn.files_modified

    def test_read_multiple_files_tracks_paths(self):
        """Test that read_multiple_files tracks all file paths from JSON."""
        self.logger.start_turn("Read multiple files")
        result_json = json.dumps({
            "files_read": {
                "/path/to/file1.py": "content1",
                "/path/to/file2.py": "content2"
            }
        })
        self.logger.add_tool_response("read_multiple_files", result_json)

        turn = self.logger.current_turn
        assert "/path/to/file1.py" in turn.files_read
        assert "/path/to/file2.py" in turn.files_read

    def test_read_multiple_files_fallback_to_regex(self):
        """Test fallback to regex when result is not valid JSON."""
        self.logger.start_turn("Read files")
        self.logger.add_tool_response(
            "read_multiple_files",
            "Read files: '/path/to/file.py'"
        )

        turn = self.logger.current_turn
        assert "/path/to/file.py" in turn.files_read

    def test_no_tracking_without_active_turn(self):
        """Test that file tracking doesn't crash without an active turn."""
        # Should not raise
        self.logger._track_file_operations("read_file", "some result")

    def test_empty_result_no_crash(self):
        """Test that empty results don't cause errors."""
        self.logger.start_turn("Test")
        self.logger.add_tool_response("read_file", "")

        turn = self.logger.current_turn
        assert turn.files_read == []

    def test_no_duplicate_tracking(self):
        """Test that the same file isn't tracked twice for the same operation."""
        self.logger.start_turn("Test dedup")
        self.logger.add_tool_response(
            "read_file", "Content of file '/path/to/file.py': ..."
        )
        self.logger.add_tool_response(
            "read_file", "Content of file '/path/to/file.py': ..."
        )

        turn = self.logger.current_turn
        assert turn.files_read.count("/path/to/file.py") == 1


class TestTurnLoggerAutoSummary:
    """Test auto-summary generation in TurnLogger."""

    def test_auto_summary_includes_tools(self):
        """Test that auto-summary includes tools used."""
        config = Config()
        logger = TurnLogger(config)

        logger.start_turn("Test query")
        logger.add_tool_call("read_file", {"file_path": "test.py"})
        logger.add_tool_response("read_file", "Content of file 'test.py': pass")

        turn = logger.complete_turn()
        assert "read_file" in turn.summary

    def test_auto_summary_includes_modified_files(self):
        """Test that auto-summary includes modified files."""
        config = Config()
        logger = TurnLogger(config)

        logger.start_turn("Edit something")
        logger.add_tool_response(
            "edit_file", "File edited successfully: '/path/to/file.py'"
        )

        turn = logger.complete_turn()
        assert "/path/to/file.py" in turn.summary

    def test_auto_summary_includes_created_files(self):
        """Test that auto-summary includes created files."""
        config = Config()
        logger = TurnLogger(config)

        logger.start_turn("Create something")
        logger.add_tool_response(
            "create_file", "File created successfully: '/path/to/new.py'"
        )

        turn = logger.complete_turn()
        assert "/path/to/new.py" in turn.summary


# ==============================================================================
# Issue #7: Structured state compression enabled by default (Medium Impact)
# ==============================================================================


class TestStructuredStateDefault:
    """Test that structured state compression is enabled by default."""

    def test_default_structured_state_enabled(self):
        """Test that TruncationStrategy defaults to structured state enabled."""
        config = Config()
        strategy = TruncationStrategy(config)

        assert strategy.use_structured_state is True

    def test_structured_state_respects_config_override(self):
        """Test that config can override the default."""
        config = Config()
        config.use_structured_state = False
        strategy = TruncationStrategy(config)

        assert strategy.use_structured_state is False

    def test_structured_state_missing_from_config_defaults_true(self):
        """Test that missing config attribute defaults to True."""
        config = Config()
        # Explicitly remove the attribute to test getattr fallback
        if hasattr(config, 'use_structured_state'):
            delattr(config, 'use_structured_state')

        strategy = TruncationStrategy(config)
        assert strategy.use_structured_state is True


# ==============================================================================
# Issue #8/#9: Error handling improvements (Medium Impact)
# ==============================================================================


class TestErrorHandling:
    """Test improved error handling in ToolExecutor."""

    def test_json_decode_error_returns_structured_failure(self):
        """Test that JSONDecodeError returns a structured ToolResult failure."""
        config = Config()
        executor = ToolExecutor(config)

        # Register a dummy tool
        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "test_tool"
        executor.register_tool(mock_tool)

        result = executor.execute_tool_call({
            "function": {
                "name": "test_tool",
                "arguments": "{invalid json"
            }
        })

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Invalid JSON" in result.result

    def test_general_exception_returns_structured_failure(self):
        """Test that general exceptions return structured ToolResult failures."""
        config = Config()
        executor = ToolExecutor(config)

        mock_tool = Mock(spec=BaseTool)
        mock_tool.get_name.return_value = "broken_tool"
        mock_tool.execute.side_effect = RuntimeError("Unexpected failure")
        executor.register_tool(mock_tool)

        result = executor.execute_tool_call({
            "function": {
                "name": "broken_tool",
                "arguments": "{}"
            }
        })

        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Unexpected failure" in result.result


# ==============================================================================
# Integration: tool_utils uses ToolResult properly (Medium Impact)
# ==============================================================================


class TestToolUtilsIntegration:
    """Test that tool_utils properly handles ToolResult from executor."""

    def test_no_string_based_error_detection(self):
        """Verify tool_utils uses ToolResult.success, not string matching."""
        from src.core import tool_utils
        import inspect

        source = inspect.getsource(tool_utils.handle_tool_calls)

        # Should NOT contain string-based error detection
        assert 'startswith("Error' not in source, \
            "tool_utils should not use string-based error detection"
        assert 'startswith("error' not in source, \
            "tool_utils should not use string-based error detection"

        # Should use structured result
        assert 'tool_result.success' in source or 'tool_success' in source, \
            "tool_utils should use ToolResult.success for error detection"

    def test_handle_tool_calls_with_no_tool_calls(self):
        """Test handle_tool_calls with response having no tool calls."""
        from src.core.tool_utils import handle_tool_calls

        mock_response = Mock()
        mock_response.tool_calls = None

        results = handle_tool_calls(mock_response, Mock(), Mock())
        assert results == []


# ==============================================================================
# ToolExecutor context manager injection (from base.py changes)
# ==============================================================================


class TestContextManagerInjection:
    """Test ToolExecutor context manager injection."""

    def test_inject_context_manager_to_all_tools(self):
        """Test that inject_context_manager sets context on all tools."""
        config = Config()
        executor = ToolExecutor(config)

        tool1 = Mock(spec=BaseTool)
        tool1.get_name.return_value = "tool_1"
        tool1.set_context_manager = Mock()

        tool2 = Mock(spec=BaseTool)
        tool2.get_name.return_value = "tool_2"
        tool2.set_context_manager = Mock()

        executor.register_tool(tool1)
        executor.register_tool(tool2)

        mock_cm = Mock()
        executor.inject_context_manager(mock_cm)

        tool1.set_context_manager.assert_called_once_with(mock_cm)
        tool2.set_context_manager.assert_called_once_with(mock_cm)
