#!/usr/bin/env python3

"""
Test configuration and fixtures for Grok Assistant tests.

This module provides common fixtures and configuration for all tests.
"""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.core.config import Config
from src.core.session import GrokSession


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_files(temp_dir: Path) -> dict[str, Path]:
    """Create sample files for testing."""
    files = {}

    # Python file
    python_file = temp_dir / "test.py"
    python_file.write_text("""#!/usr/bin/env python3

def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
    files["python"] = python_file

    # Text file
    text_file = temp_dir / "readme.txt"
    text_file.write_text("This is a test file for Grok Assistant.")
    files["text"] = text_file

    # JSON file
    json_file = temp_dir / "config.json"
    json_file.write_text('{"name": "test", "version": "1.0"}')
    files["json"] = json_file

    # Binary file (simulate)
    binary_file = temp_dir / "binary.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")
    files["binary"] = binary_file

    # Subdirectory with files
    sub_dir = temp_dir / "subdir"
    sub_dir.mkdir()
    sub_file = sub_dir / "nested.txt"
    sub_file.write_text("Nested file content")
    files["nested"] = sub_file

    return files


@pytest.fixture
def mock_config(temp_dir: Path) -> Config:
    """Create a mock configuration for testing."""
    config = Config()
    config.base_dir = temp_dir
    config.fuzzy_available = True
    config.fuzzy_enabled_by_default = False
    config.max_file_content_size_create = 1024 * 1024
    config.max_files_in_add_dir = 100
    config.require_bash_confirmation = False
    config.require_powershell_confirmation = False
    return config


@pytest.fixture
def clean_config(tmp_path):
    """
    Provide a Config with no user config.json interference.

    This fixture creates a Config instance with a temporary directory,
    ensuring tests are isolated from the user's actual config.json file.
    Useful for testing default behavior without config overrides.
    """
    # Create a temporary directory for config
    config_dir = tmp_path / ".grok"
    config_dir.mkdir()

    # Create Config with temporary base directory
    config = Config()
    config.base_dir = tmp_path
    config.config_file = config_dir / "config.json"

    # Ensure use_extended_context is False (default behavior)
    config.use_extended_context = False

    return config


@pytest.fixture
def mock_client():
    """Create a mock xAI client for testing."""
    client = Mock()
    chat = Mock()
    chat.create = Mock()
    client.chat = chat
    return client


@pytest.fixture
def mock_session(mock_client, mock_config):
    """Create a mock session for testing."""
    session = Mock(spec=GrokSession)
    session.client = mock_client
    session.config = mock_config
    session.model = "grok-3"
    session.is_reasoner = False
    session.history = []
    session.get_conversation_history.return_value = []
    session.add_message = Mock()
    session.get_response = Mock()
    return session


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {"role": "system", "content": "You are Grok Assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! How can I help you?"},
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "2+2 equals 4."},
    ]


@pytest.fixture
def mock_console():
    """Create a mock console for testing UI components."""
    console = Mock()
    console.print = Mock()
    console.clear = Mock()
    return console


@pytest.fixture
def mock_ui():
    """Create a mock UI adapter for testing."""
    from src.ui.adapter import MockUIAdapter

    return MockUIAdapter()


@pytest.fixture
def memory_manager(mock_config):
    """Create a memory manager for testing with clean state."""
    from src.core.memory_manager import MemoryManager

    mm = MemoryManager(mock_config)
    # Clear any existing memories to ensure test isolation
    mm.clear_global_memories()
    mm.clear_directory_memories()
    return mm


@pytest.fixture
def memory_service(memory_manager):
    """Create a memory service for testing with clean state."""
    from src.services import MemoryService

    return MemoryService(memory_manager)


@pytest.fixture
def file_service(mock_config):
    """Create a file service for testing."""
    from src.services import FileService

    return FileService(mock_config)


@pytest.fixture
def context_manager(mock_config):
    """Create a context manager for testing."""
    from src.core.context_manager import ContextManager

    return ContextManager(mock_config)


@pytest.fixture
def context_service(context_manager):
    """Create a context service for testing."""
    from src.services import ContextService

    return ContextService(context_manager)


class TestFileContent:
    """Helper class for creating test file content."""

    @staticmethod
    def large_file_content(size_kb: int = 100) -> str:
        """Generate large file content for testing size limits."""
        line = "This is a test line for large file content.\n"
        lines_needed = (size_kb * 1024) // len(line.encode("utf-8"))
        return line * lines_needed

    @staticmethod
    def unicode_content() -> str:
        """Generate Unicode content for encoding tests."""
        return "Hello 世界! 🌍 Testing UTF-8 encoding with émojis and accénts."

    @staticmethod
    def code_content() -> str:
        """Generate code content for syntax highlighting tests."""
        return '''def fibonacci(n):
    """Generate Fibonacci sequence up to n."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# Test the function
print(fibonacci(10))
'''


# Test markers for categorizing tests
pytest_markers = [
    "unit: Unit tests for individual components",
    "integration: Integration tests for component interaction",
    "slow: Tests that take longer to run",
    "security: Security-related tests",
    "ui: User interface tests",
    "commands: Command handler tests",
    "tools: Tool execution tests",
    "utils: Utility function tests",
]
