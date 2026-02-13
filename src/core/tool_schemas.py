#!/usr/bin/env python3

"""
Tool Schema Definitions for Grok Assistant

Extracted from Config to eliminate the god-class pattern.
Contains all static tool schema definitions used by the xAI SDK API.

Tools can gradually migrate their schemas to co-located get_schema() methods
on BaseTool subclasses. Schemas defined here serve as the fallback.
"""

from xai_sdk.chat import tool


def get_static_tool_schemas() -> list:
    """
    Get all statically-defined tool schemas for the xAI SDK API.

    Returns:
        List of xai_sdk tool schema objects
    """
    return [
        tool(
            name="read_file",
            description="Read the content of a single file from the filesystem",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to read",
                    },
                },
                "required": ["file_path"],
            },
        ),
        tool(
            name="read_multiple_files",
            description="Read the content of multiple files",
            parameters={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of file paths to read",
                    },
                },
                "required": ["file_paths"],
            },
        ),
        tool(
            name="create_file",
            description="Create or overwrite a file",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path for the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content for the file",
                    },
                },
                "required": ["file_path", "content"],
            },
        ),
        tool(
            name="create_multiple_files",
            description="Create multiple files",
            parameters={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["path", "content"],
                        },
                        "description": "Array of files to create (path, content)",
                    },
                },
                "required": ["files"],
            },
        ),
        tool(
            name="edit_file",
            description="Edit a file by replacing a snippet (fuzzy matching available with /fuzzy flag)",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                    "original_snippet": {
                        "type": "string",
                        "description": "Snippet to replace",
                    },
                    "new_snippet": {
                        "type": "string",
                        "description": "Replacement snippet",
                    },
                },
                "required": ["file_path", "original_snippet", "new_snippet"],
            },
        ),
        tool(
            name="run_powershell",
            description="Run a PowerShell command with security confirmation (Windows/Cross-platform PowerShell Core).",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The PowerShell command to execute",
                    },
                },
                "required": ["command"],
            },
        ),
        tool(
            name="run_bash",
            description="Run a bash command with security confirmation (macOS/Linux/WSL).",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                },
                "required": ["command"],
            },
        ),
        tool(
            name="run_bash_background",
            description="Run a bash command in the background without blocking. Returns immediately with a job ID. Use this for long-running commands, monitoring tasks, or when you want to continue working while the command runs. Check status with check_background_job().",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute in background",
                    },
                },
                "required": ["command"],
            },
        ),
        tool(
            name="run_powershell_background",
            description="Run a PowerShell command in the background without blocking. Returns immediately with a job ID. Use this for long-running commands or when you want to continue working. Check status with check_background_job().",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The PowerShell command to execute in background",
                    },
                },
                "required": ["command"],
            },
        ),
        tool(
            name="check_background_job",
            description="Check the status and output of a background job. Returns job status, runtime, stdout, and stderr.",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The job ID returned from run_bash_background or run_powershell_background",
                    },
                },
                "required": ["job_id"],
            },
        ),
        tool(
            name="kill_background_job",
            description="Kill a running background job by its ID.",
            parameters={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "The job ID to kill",
                    },
                },
                "required": ["job_id"],
            },
        ),
        tool(
            name="list_background_jobs",
            description="List all background jobs with their status, runtime, and commands. Use this to see what jobs are running or completed.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        tool(
            name="save_memory",
            description="Save important information that should persist across conversations and context truncations. Use this for user preferences, architectural decisions, important facts, and project context that you want to remember.",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Important information to remember. Be concise but specific.",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["user_preference", "architectural_decision", "important_fact", "project_context"],
                        "description": "Type of memory: user_preference (user's preferred tools/patterns), architectural_decision (project structure/tech choices), important_fact (critical project info), project_context (specific constraints/requirements)",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["directory", "global"],
                        "default": "directory",
                        "description": "Memory scope: 'directory' for current project only, 'global' for all projects",
                    },
                },
                "required": ["content", "type"],
            },
        ),
        tool(
            name="change_working_directory",
            description="Change the current working directory for file operations. Use this when you need to work in a different directory.",
            parameters={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to change to. Can be absolute, relative, or use ~ for home directory.",
                    },
                },
                "required": ["directory_path"],
            },
        ),
        tool(
            name="grep_codebase",
            description="Search for regex patterns across multiple files in the codebase. Returns matches with file paths, line numbers, and highlighted context. Use this to find usage patterns, definitions, or specific code snippets.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for (e.g., 'class.*Tool', 'def\\s+\\w+\\(', 'TODO.*bug')",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern for files to search (default: **/*.py). Examples: '**/*.js', 'src/**/*.py', '*.md'",
                        "default": "**/*.py",
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search is case-sensitive (default: false)",
                        "default": False,
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of matches to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["pattern"],
            },
        ),
        tool(
            name="inspect_code_structure",
            description="Inspect Python file structure using AST analysis. Returns imports, classes, functions, and docstrings without reading the entire file content. Use this to understand file organization before editing or to find specific classes/functions.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to Python file to inspect (.py or .pyw)",
                    },
                    "include_docstrings": {
                        "type": "boolean",
                        "description": "Whether to include docstrings in output (default: true)",
                        "default": True,
                    },
                    "format": {
                        "type": "string",
                        "enum": ["summary", "json"],
                        "description": "Output format: 'summary' for human-readable, 'json' for structured data (default: summary)",
                        "default": "summary",
                    },
                },
                "required": ["file_path"],
            },
        ),
        tool(
            name="search_replace_file",
            description="Perform deterministic search and replace in a file. Requires EXACTLY 1 match by default (strict mode). Use this for precise, reliable edits. For Python files, syntax is validated before saving. Include enough context in search_block to ensure a unique match.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to edit",
                    },
                    "search_block": {
                        "type": "string",
                        "description": "Exact code block to search for. Must match EXACTLY (whitespace-normalized). Include enough surrounding code to ensure only 1 match.",
                    },
                    "replace_block": {
                        "type": "string",
                        "description": "Replacement code block. Will inherit indentation from matched location.",
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "If true, fail if not exactly 1 match. If false, replace all matches (default: true)",
                        "default": True,
                    },
                },
                "required": ["file_path", "search_block", "replace_block"],
            },
        ),
        tool(
            name="apply_diff_patch",
            description="Apply a unified diff patch to a file. More reliable than search_replace for complex multi-line edits. Use unified diff format (like 'diff -u' output). Python files are validated for syntax after patching.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to patch",
                    },
                    "diff": {
                        "type": "string",
                        "description": "Unified diff string. Format: @@ -start,count +start,count @@ followed by context ( ), deletions (-), and additions (+) lines.",
                    },
                },
                "required": ["file_path", "diff"],
            },
        ),
        # Task management tools
        tool(
            name="add_task",
            description="Add a new task to your internal todo list. Use this to track multi-step operations and ensure nothing is forgotten. Tasks persist across turns until completed or cleared.",
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Clear description of what needs to be done",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Task priority (default: normal)",
                        "default": "normal",
                    },
                },
                "required": ["description"],
            },
        ),
        tool(
            name="complete_task",
            description="Mark a task as completed. Use this when you finish a task to track progress.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to complete (format: task_XXXXXXXX)",
                    },
                },
                "required": ["task_id"],
            },
        ),
        tool(
            name="list_tasks",
            description="List your current tasks with optional filtering. Use this to see what work remains.",
            parameters={
                "type": "object",
                "properties": {
                    "show_completed": {
                        "type": "boolean",
                        "description": "Include completed tasks in the list (default: false)",
                        "default": False,
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Filter by priority (optional)",
                    },
                },
                "required": [],
            },
        ),
        tool(
            name="remove_task",
            description="Remove a task from your todo list. Use this to clean up tasks that are no longer relevant.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID of the task to remove (format: task_XXXXXXXX)",
                    },
                },
                "required": ["task_id"],
            },
        ),
        tool(
            name="create_tool",
            description="Create a new custom tool that extends your capabilities. Only available in self-evolving mode (/self). The tool will be validated for safety and saved to ~/.grok/custom_tools/.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique tool name (snake_case, e.g., 'analyze_json')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of what the tool does",
                    },
                    "source_code": {
                        "type": "string",
                        "description": "Python source code. Must define a class inheriting from BaseTool with get_name() and execute() methods, plus a create_tool(config) factory function.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "JSON schema for tool parameters",
                        "default": {"type": "object", "properties": {}, "required": []},
                    },
                },
                "required": ["name", "description", "source_code"],
            },
        ),
        tool(
            name="task_completed",
            description="Call this when you have FULLY completed the user's request AND are ready for their next instruction. Do NOT call this in the middle of multi-step tasks. This may trigger context management options if token usage is high.",
            parameters={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A concise summary of what was accomplished (1-2 sentences)."
                    },
                    "next_steps": {
                        "type": "string",
                        "description": "Optional suggestions for what the user might want to do next."
                    }
                },
                "required": ["summary"]
            },
        ),
    ]
