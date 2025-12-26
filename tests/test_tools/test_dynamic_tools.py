"""
Unit tests for dynamic tool system (self-evolving AI tools).

Tests ToolValidator, DynamicToolLoader, and CreateToolTool.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.dynamic_tools import (
    ToolValidator,
    DynamicToolLoader,
    CreateToolTool,
    create_dynamic_tools
)
from src.tools.base import ToolResult
from src.core.config import Config


class TestToolValidator:
    """Test ToolValidator security and validation."""

    def test_validator_blocks_subprocess(self):
        """Verify subprocess import is blocked."""
        source = """
import subprocess
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        return ToolResult.ok("test")

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "Blocked import" in error or "subprocess" in error.lower()

    def test_validator_blocks_eval(self):
        """Verify eval() calls are blocked."""
        source = """
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        result = eval(args['code'])
        return ToolResult.ok(result)

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "eval" in error.lower() or "blocked call" in error.lower()

    def test_validator_blocks_exec(self):
        """Verify exec() calls are blocked."""
        source = """
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        exec(args['code'])
        return ToolResult.ok("executed")

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "exec" in error.lower() or "blocked call" in error.lower()

    def test_validator_blocks_pickle(self):
        """Verify pickle import is blocked."""
        source = """
import pickle
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        return ToolResult.ok("test")

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "pickle" in error.lower() or "blocked import" in error.lower()

    def test_validator_requires_basetool(self):
        """Verify BaseTool inheritance is required."""
        source = """
class MyTool:
    def get_name(self):
        return "test"

    def execute(self, args):
        return "result"

def create_tool(config):
    return MyTool()
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "BaseTool" in error or "inherit" in error.lower()

    def test_validator_requires_factory_function(self):
        """Verify create_tool() factory function is required."""
        source = """
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        return ToolResult.ok("test")
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "create_tool" in error.lower() or "factory" in error.lower()

    def test_validator_accepts_valid_tool(self):
        """Verify valid tool passes validation."""
        source = """
from src.tools.base import BaseTool, ToolResult

class MyTool(BaseTool):
    def get_name(self):
        return "my_test_tool"

    def execute(self, args):
        return ToolResult.ok("Hello World")

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert is_valid, f"Valid tool rejected: {error}"
        assert error is None or error == ""

    def test_validator_blocks_os_system(self):
        """Verify os.system is blocked."""
        source = """
import os
from src.tools.base import BaseTool

class MyTool(BaseTool):
    def get_name(self):
        return "test"

    def execute(self, args):
        os.system('ls')
        return ToolResult.ok("test")

def create_tool(config):
    return MyTool(config)
"""
        is_valid, error = ToolValidator.validate_tool_code(source)
        assert not is_valid
        assert "os.system" in error.lower() or "blocked" in error.lower()


class TestDynamicToolLoader:
    """Test DynamicToolLoader functionality."""

    @pytest.fixture
    def temp_tools_dir(self):
        """Create temporary tools directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def loader(self, temp_tools_dir):
        """Create loader with temp directory."""
        config = Config()
        config.custom_tools_dir = temp_tools_dir
        return DynamicToolLoader(config)

    def test_loader_creates_directory(self, temp_tools_dir):
        """Verify loader creates tools directory."""
        # Remove directory
        shutil.rmtree(temp_tools_dir)
        assert not temp_tools_dir.exists()

        # Create loader
        config = Config()
        config.custom_tools_dir = temp_tools_dir
        loader = DynamicToolLoader(config)

        # Directory should be created
        assert temp_tools_dir.exists()
        assert (temp_tools_dir / "__init__.py").exists()

    def test_loader_saves_tool(self, loader, temp_tools_dir):
        """Verify loader saves tool to file."""
        source = """
from src.tools.base import BaseTool, ToolResult

class ReverseTool(BaseTool):
    def get_name(self):
        return "reverse_string"

    def execute(self, args):
        text = args.get('text', '')
        return ToolResult.ok(text[::-1])

def create_tool(config):
    return ReverseTool(config)
"""
        schema = {
            "name": "reverse_string",
            "description": "Reverse a string",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"}
                }
            }
        }

        success, error = loader.save_tool("reverse_string", source, schema)

        assert success, f"Failed to save tool: {error}"
        assert (temp_tools_dir / "reverse_string.py").exists()

    def test_loader_loads_tool(self, loader, temp_tools_dir):
        """Verify loader loads saved tool."""
        # Save a tool first
        source = """
from src.tools.base import BaseTool, ToolResult

class TestTool(BaseTool):
    def get_name(self):
        return "test_tool"

    def execute(self, args):
        return ToolResult.ok("test result")

def create_tool(config):
    return TestTool(config)
"""
        schema = {
            "name": "test_tool",
            "description": "Test tool",
            "parameters": {"type": "object", "properties": {}}
        }

        loader.save_tool("test_tool", source, schema)

        # Load all tools
        tools = loader.load_all_tools()

        assert len(tools) > 0
        tool_names = [tool.get_name() for tool in tools]
        assert "test_tool" in tool_names

    def test_loader_skips_invalid_tools(self, loader, temp_tools_dir):
        """Verify loader skips tools with syntax errors."""
        # Create invalid tool file
        invalid_file = temp_tools_dir / "invalid_tool.py"
        invalid_file.write_text("this is not valid python code <<<")

        # Load tools - should not crash
        tools = loader.load_all_tools()

        # Invalid tool should be skipped
        tool_names = [tool.get_name() for tool in tools]
        assert "invalid_tool" not in tool_names

    def test_loader_get_tool_schemas(self, loader, temp_tools_dir):
        """Verify loader returns tool schemas."""
        # Save a tool
        source = """
from src.tools.base import BaseTool, ToolResult

class SchemaTool(BaseTool):
    def get_name(self):
        return "schema_tool"

    def execute(self, args):
        return ToolResult.ok("test")

def create_tool(config):
    return SchemaTool(config)
"""
        schema = {
            "name": "schema_tool",
            "description": "Schema test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }

        loader.save_tool("schema_tool", source, schema)

        # Get schemas
        schemas = loader.get_tool_schemas()

        assert len(schemas) > 0
        schema_names = [s["name"] for s in schemas]
        assert "schema_tool" in schema_names


class TestCreateToolTool:
    """Test CreateToolTool (AI-facing tool)."""

    @pytest.fixture
    def temp_tools_dir(self):
        """Create temporary tools directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def create_tool_tool(self, temp_tools_dir):
        """Create CreateToolTool instance."""
        config = Config()
        config.custom_tools_dir = temp_tools_dir
        loader = DynamicToolLoader(config)
        return CreateToolTool(config, loader)

    def test_create_tool_validates_input(self, create_tool_tool):
        """Verify CreateToolTool validates dangerous code."""
        args = {
            "name": "bad_tool",
            "description": "Dangerous tool",
            "source_code": """
import subprocess
from src.tools.base import BaseTool

class BadTool(BaseTool):
    def get_name(self):
        return "bad_tool"

    def execute(self, args):
        subprocess.call(['ls'])
        return ToolResult.ok("done")

def create_tool(config):
    return BadTool(config)
"""
        }

        result = create_tool_tool.execute(args)

        assert not result.success
        assert "blocked" in result.error.lower() or "subprocess" in result.error.lower()

    def test_create_tool_success(self, create_tool_tool, temp_tools_dir):
        """Verify CreateToolTool successfully creates valid tool."""
        args = {
            "name": "hello_tool",
            "description": "Says hello",
            "source_code": """
from src.tools.base import BaseTool, ToolResult

class HelloTool(BaseTool):
    def get_name(self):
        return "hello_tool"

    def execute(self, args):
        name = args.get('name', 'World')
        return ToolResult.ok(f"Hello, {name}!")

def create_tool(config):
    return HelloTool(config)
""",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"}
                }
            }
        }

        result = create_tool_tool.execute(args)

        assert result.success, f"Tool creation failed: {result.error}"
        assert (temp_tools_dir / "hello_tool.py").exists()

    def test_create_tool_with_minimal_args(self, create_tool_tool):
        """Verify CreateToolTool works with minimal arguments."""
        args = {
            "name": "minimal_tool",
            "description": "Minimal tool",
            "source_code": """
from src.tools.base import BaseTool, ToolResult

class MinimalTool(BaseTool):
    def get_name(self):
        return "minimal_tool"

    def execute(self, args):
        return ToolResult.ok("minimal")

def create_tool(config):
    return MinimalTool(config)
"""
        }

        result = create_tool_tool.execute(args)

        assert result.success


class TestIntegration:
    """Integration tests for dynamic tool system."""

    def test_create_dynamic_tools_factory(self):
        """Verify create_dynamic_tools factory function."""
        config = Config()

        # Create temporary directory for test
        with tempfile.TemporaryDirectory() as temp_dir:
            config.custom_tools_dir = Path(temp_dir)

            tools, loader = create_dynamic_tools(config)

            # Should return CreateToolTool
            assert len(tools) >= 1
            assert any(tool.get_name() == "create_tool" for tool in tools)

            # Loader should be returned
            assert loader is not None
            assert isinstance(loader, DynamicToolLoader)

    def test_end_to_end_tool_creation(self):
        """Test full workflow: create → save → load → execute."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.custom_tools_dir = Path(temp_dir)

            # Step 1: Create loader and CreateToolTool
            loader = DynamicToolLoader(config)
            create_tool_tool = CreateToolTool(config, loader)

            # Step 2: Create a tool via CreateToolTool
            args = {
                "name": "square_tool",
                "description": "Squares a number",
                "source_code": """
from src.tools.base import BaseTool, ToolResult

class SquareTool(BaseTool):
    def get_name(self):
        return "square_tool"

    def execute(self, args):
        num = args.get('number', 0)
        result = num * num
        return ToolResult.ok(f"Square of {num} is {result}")

def create_tool(config):
    return SquareTool(config)
""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "integer"}
                    }
                }
            }

            result = create_tool_tool.execute(args)
            assert result.success

            # Step 3: Load the tool
            tools = loader.load_all_tools()
            square_tool = next((t for t in tools if t.get_name() == "square_tool"), None)
            assert square_tool is not None

            # Step 4: Execute the tool
            tool_result = square_tool.execute({"number": 5})
            assert tool_result.success
            assert "25" in tool_result.result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
