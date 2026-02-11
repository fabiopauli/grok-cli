#!/usr/bin/env python3

"""
Tests for markdown rendering functionality in UI module.

Tests the display_assistant_response function with both plain text
and markdown rendering modes.
"""

from unittest.mock import call, patch

from rich.markdown import Markdown

from src.ui.console import display_assistant_response


class TestPlainTextRendering:
    """Test plain text rendering (default mode)."""

    def test_plain_text_default(self, capsys):
        """Test plain text rendering with markdown disabled (default)."""
        content = "This is a plain text response."

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=False)

            # Verify console.print was called correctly
            calls = mock_console.print.call_args_list
            assert len(calls) == 3  # newline before, content, newline after

            # Check the middle call contains the assistant response
            assert calls[1] == call("Assistant: This is a plain text response.")

    def test_plain_text_with_markdown_content(self):
        """Test that markdown syntax is shown literally when markdown is disabled."""
        content = "# Header\n**bold** and *italic*"

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=False)

            # Should show markdown syntax literally
            calls = mock_console.print.call_args_list
            # The content should be in the middle call with Assistant: prefix
            assert calls[1][0][0] == f"Assistant: {content}"


class TestMarkdownRendering:
    """Test markdown rendering when enabled."""

    def test_markdown_enabled(self):
        """Test markdown rendering when enabled."""
        content = "# Test Header\n\nThis is **bold** text."

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=True)

            # Verify Markdown object was passed to console.print
            calls = mock_console.print.call_args_list
            assert len(calls) == 3  # newline before, markdown content, newline after

            # Check that a Markdown object was passed
            middle_call_args = calls[1][0]
            assert len(middle_call_args) == 1
            assert isinstance(middle_call_args[0], Markdown)

    def test_markdown_code_blocks(self):
        """Test code blocks with syntax highlighting."""
        content = '''Here's some code:

```python
def hello():
    print("Hello World")
```
'''

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=True, code_theme="monokai")

            # Verify Markdown was created with correct theme
            calls = mock_console.print.call_args_list
            middle_call_args = calls[1][0]
            md_object = middle_call_args[0]

            # Verify it's a Markdown object
            assert isinstance(md_object, Markdown)

    def test_markdown_headers_and_formatting(self):
        """Test headers, bold, italic, inline code."""
        content = '''# Header 1
## Header 2

This is **bold** and *italic* text.
Inline code: `print("test")`
'''

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=True)

            calls = mock_console.print.call_args_list
            middle_call_args = calls[1][0]
            assert isinstance(middle_call_args[0], Markdown)

    def test_markdown_lists(self):
        """Test lists rendering."""
        content = '''
- Item 1
- Item 2
- Item 3

1. First
2. Second
3. Third
'''

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=True)

            calls = mock_console.print.call_args_list
            middle_call_args = calls[1][0]
            assert isinstance(middle_call_args[0], Markdown)

    def test_custom_code_theme(self):
        """Test custom code theme parameter."""
        content = "```python\ncode\n```"

        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(content, enable_markdown=True, code_theme="github-dark")

            # Verify Markdown was created (theme is passed to constructor)
            calls = mock_console.print.call_args_list
            middle_call_args = calls[1][0]
            assert isinstance(middle_call_args[0], Markdown)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_content(self):
        """Test handling of empty content."""
        with patch('src.ui.console._console') as mock_console:
            display_assistant_response("", enable_markdown=True)

            # Should not print anything for empty content
            assert mock_console.print.call_count == 0

    def test_none_content(self):
        """Test handling of None content."""
        with patch('src.ui.console._console') as mock_console:
            display_assistant_response(None, enable_markdown=True)

            # Should not print anything for None content
            assert mock_console.print.call_count == 0

    def test_whitespace_only_content(self):
        """Test handling of whitespace-only content."""
        with patch('src.ui.console._console') as mock_console:
            display_assistant_response("   \n\n  ", enable_markdown=True)

            # Should not print anything for whitespace-only content
            assert mock_console.print.call_count == 0

    def test_graceful_fallback_on_markdown_error(self):
        """Test fallback to plain text if markdown rendering fails."""
        content = "Test content"

        with patch('src.ui.console._console') as mock_console:
            # Mock Markdown to raise an exception
            with patch('src.ui.console.Markdown', side_effect=Exception("Markdown error")):
                display_assistant_response(content, enable_markdown=True)

                # Should have printed warning and fallback to plain text
                calls = mock_console.print.call_args_list

                # Should have: newline, warning, fallback content, newline
                assert len(calls) == 4

                # Check for warning message
                warning_call = calls[1]
                assert "Warning: Markdown rendering failed" in str(warning_call)

                # Check for fallback content
                fallback_call = calls[2]
                assert "Assistant: Test content" in str(fallback_call)


class TestConfigIntegration:
    """Test config integration for markdown rendering."""

    def test_config_markdown_rendering_field_exists(self):
        """Test that markdown rendering config field exists."""
        from dataclasses import fields

        from src.core.config import Config

        # Check the field exists in the dataclass
        config_field_names = {f.name for f in fields(Config)}

        assert 'enable_markdown_rendering' in config_field_names
        assert 'markdown_code_theme' in config_field_names

    def test_config_theme_default(self):
        """Test default code theme is monokai."""
        from src.core.config import Config
        config = Config()
        assert config.markdown_code_theme == "monokai"

    def test_config_loading_from_dict(self):
        """Test loading markdown config from dictionary."""
        from src.core.config import Config
        config = Config()

        # Simulate loading from config file
        config_data = {
            "ui": {
                "enable_markdown_rendering": True,
                "markdown_code_theme": "github-dark"
            }
        }

        config._apply_config_data(config_data)

        assert config.enable_markdown_rendering is True
        assert config.markdown_code_theme == "github-dark"
