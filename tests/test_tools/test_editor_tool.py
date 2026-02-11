"""
Unit tests for editor tools (diff-based editing).

Tests ApplyDiffPatchTool for unified diff application.
"""

import tempfile
from pathlib import Path

import pytest

from src.core.config import Config
from src.tools.editor_tool import ApplyDiffPatchTool


class TestApplyDiffPatchTool:
    """Test ApplyDiffPatchTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create ApplyDiffPatchTool instance."""
        config = Config()
        config.test_mode = True  # Allow temp paths in tests
        return ApplyDiffPatchTool(config)

    @pytest.fixture
    def temp_file(self):
        """Create temporary test file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def hello():
    print("Hello")

def world():
    print("World")

def goodbye():
    print("Goodbye")
""")
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_apply_simple_diff(self, tool, temp_file):
        """Test applying a simple single-line diff."""
        diff = """@@ -1,2 +1,2 @@
 def hello():
-    print("Hello")
+    print("Hello, World!")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success, f"Diff application failed: {result.error}"
        content = temp_file.read_text()
        assert 'print("Hello, World!")' in content
        assert 'print("Hello")' not in content

    def test_apply_multiline_diff(self, tool, temp_file):
        """Test applying a multi-line diff with multiple hunks."""
        diff = """@@ -1,3 +1,3 @@
 def hello():
-    print("Hello")
+    print("Greetings")

@@ -4,2 +4,2 @@
 def world():
-    print("World")
+    print("Universe")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success, f"Diff application failed: {result.error}"
        content = temp_file.read_text()
        assert 'print("Greetings")' in content
        assert 'print("Universe")' in content
        assert 'print("Hello")' not in content
        assert 'print("World")' not in content

    def test_apply_diff_preserves_unchanged_lines(self, tool, temp_file):
        """Test that unchanged lines are preserved."""
        diff = """@@ -1,2 +1,2 @@
 def hello():
-    print("Hello")
+    print("Modified")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success
        content = temp_file.read_text()
        # These lines should remain unchanged
        assert 'def world():' in content
        assert 'def goodbye():' in content
        assert 'print("Goodbye")' in content

    def test_apply_diff_validates_python_syntax(self, tool, temp_file):
        """Test that Python syntax is validated after applying diff."""
        # This diff would create invalid Python syntax
        diff = """@@ -1,3 +1,3 @@
 def hello():
-    print("Hello")
+    print("Hello"  # Missing closing parenthesis

"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        # Should fail due to syntax error
        assert not result.success
        assert "syntax" in result.error.lower() or "invalid" in result.error.lower()

    def test_apply_diff_handles_invalid_format(self, tool, temp_file):
        """Test handling of invalid diff format."""
        # Invalid diff - missing hunk header
        diff = """- old line
+ new line
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert not result.success
        assert "diff" in result.error.lower() or "invalid" in result.error.lower() or "format" in result.error.lower()

    def test_apply_diff_handles_nonexistent_file(self, tool):
        """Test handling of nonexistent file."""
        diff = """@@ -1,1 +1,1 @@
-old
+new
"""
        args = {
            "file_path": "/nonexistent/file.py",
            "diff": diff
        }

        result = tool.execute(args)

        assert not result.success
        assert "not found" in result.error.lower() or "exist" in result.error.lower()

    def test_apply_diff_with_additions(self, tool, temp_file):
        """Test diff that adds new lines."""
        diff = """@@ -1,2 +1,4 @@
 def hello():
     print("Hello")
+    print("Extra line 1")
+    print("Extra line 2")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success
        content = temp_file.read_text()
        assert 'print("Extra line 1")' in content
        assert 'print("Extra line 2")' in content

    def test_apply_diff_with_deletions(self, tool, temp_file):
        """Test diff that deletes lines."""
        diff = """@@ -3,5 +3,3 @@

-def world():
-    print("World")
-
 def goodbye():
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success
        content = temp_file.read_text()
        assert 'def world():' not in content
        assert 'print("World")' not in content
        # goodbye should still exist
        assert 'def goodbye():' in content

    def test_apply_diff_empty_hunks(self, tool, temp_file):
        """Test diff with empty hunks (should skip gracefully)."""
        diff = """@@ -1,2 +1,2 @@
 def hello():
     print("Hello")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        # Should succeed even with no actual changes
        assert result.success

    def test_apply_diff_to_non_python_file(self, tool):
        """Test applying diff to non-Python file (should skip syntax validation)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            temp_path = Path(f.name)

        try:
            diff = """@@ -1,1 +1,1 @@
-Line 1
+Modified Line 1
"""
            args = {
                "file_path": str(temp_path),
                "diff": diff
            }

            result = tool.execute(args)

            assert result.success
            content = temp_path.read_text()
            assert "Modified Line 1" in content
        finally:
            temp_path.unlink()

    def test_apply_diff_sequential_hunks(self, tool, temp_file):
        """Test multiple hunks applied sequentially with offset tracking."""
        diff = """@@ -1,2 +1,2 @@
 def hello():
-    print("Hello")
+    print("A")

@@ -4,2 +4,2 @@
 def world():
-    print("World")
+    print("B")

@@ -7,2 +7,2 @@
 def goodbye():
-    print("Goodbye")
+    print("C")
"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success
        content = temp_file.read_text()
        assert 'print("A")' in content
        assert 'print("B")' in content
        assert 'print("C")' in content

    def test_tool_name(self, tool):
        """Test tool name is correct."""
        assert tool.get_name() == "apply_diff_patch"

    def test_apply_diff_with_context_lines(self, tool, temp_file):
        """Test diff with context lines (lines starting with space)."""
        diff = """@@ -1,3 +1,3 @@
 def hello():
-    print("Hello")
+    print("Modified")

"""
        args = {
            "file_path": str(temp_file),
            "diff": diff
        }

        result = tool.execute(args)

        assert result.success
        content = temp_file.read_text()
        assert 'print("Modified")' in content
        # Context lines should be preserved
        assert 'def hello():' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
