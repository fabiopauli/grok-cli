#!/usr/bin/env python3

"""
Code Execution Reminder Tool for Grok Assistant

A meta-tool that reminds the AI it can write and execute code to solve problems.
Use with caution - only when the AI seems to be overthinking instead of coding.
"""

from typing import Any

from .base import BaseTool, ToolResult


class CodeExecutionReminderTool(BaseTool):
    """
    Reminder tool that the AI can write and execute Python code.

    This tool should be used sparingly, only when:
    - Complex calculations or data processing is needed
    - Testing hypotheses or validating approaches
    - Generating test data or examples
    - When shell commands are too limited

    CAUTION: Execution happens in the user's environment. Ensure code is safe.
    """

    def get_name(self) -> str:
        return "remind_code_execution"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """
        Returns a reminder that the AI can write and execute code.

        Args:
            args: Dict with optional 'task_description' explaining what needs to be done

        Returns:
            Reminder message with guidance on code execution
        """
        task_desc = args.get("task_description", "the current task")

        reminder = f"""
Code Execution Capability Reminder

You CAN write and execute Python code to solve "{task_desc}".

**How to do it:**
1. Use create_file to write a Python script (e.g., /tmp/solve_task.py)
2. Use run_bash to execute it: python /tmp/solve_task.py
3. Analyze the output and use results to continue

**Good use cases:**
- Complex calculations or data transformations
- Testing algorithms or logic
- Generating test data, examples, or fixtures
- Parsing/processing structured data (JSON, CSV, etc.)
- Validating approaches before implementing in main codebase
- Quick prototyping of solutions

**Safety considerations:**
- Code runs in user's environment - ensure it's safe
- Avoid file system modifications outside /tmp unless necessary
- Don't install packages without user permission
- Keep scripts focused and temporary

**Example workflow:**
1. Write script: create_file("/tmp/calculate.py", "# Your code here...")
2. Execute: run_bash("python /tmp/calculate.py")
3. Use output: Parse results and apply to your task

Remember: You're an AI that can CODE, not just suggest. Take action!
"""

        return ToolResult.ok(reminder.strip())

    def get_schema(self) -> dict[str, Any]:
        """Get the JSON schema for this tool."""
        return {
            "name": self.get_name(),
            "description": (
                "RARE USE: Reminds you that you can write and execute Python code to solve complex problems. "
                "Use this when you find yourself overthinking instead of coding, or when shell commands are insufficient. "
                "You can create temporary Python scripts and run them to: perform calculations, process data, "
                "test hypotheses, generate examples, or validate approaches. "
                "CAUTION: Code executes in the user's environment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Brief description of what you're trying to accomplish that might benefit from code execution"
                    }
                },
                "required": []
            }
        }


def create_code_execution_tools(config):
    """
    Create code execution reminder tools.

    Args:
        config: Configuration object

    Returns:
        List of code execution related tools
    """
    return [CodeExecutionReminderTool(config)]
