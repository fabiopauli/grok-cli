#!/usr/bin/env python3

"""
Configuration management for Grok Assistant

This module provides a Config class that eliminates global state
and provides dependency injection for configuration values.
"""

import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Set, Optional
from dataclasses import dataclass, field
from xai_sdk.chat import tool


@dataclass
class Config:
    """
    Configuration class that encapsulates all application settings
    and eliminates global state dependencies.
    """
    
    # Core paths
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    config_file: Optional[Path] = None
    
    # Model settings
    default_model: str = "grok-4-1-fast-non-reasoning"
    reasoner_model: str = "grok-4-1-fast-reasoning"
    coder_model: str = "grok-code-fast-1"
    grok4_model: str = "grok-4-fast-non-reasoning"
    grok4_reasoner_model: str = "grok-4-fast-reasoning"
    current_model: str = "grok-4-1-fast-non-reasoning"
    is_reasoner: bool = False
    use_extended_context: bool = False
    
    # File limits
    max_files_in_add_dir: int = 1000
    max_file_size_in_add_dir: int = 5_000_000
    max_file_content_size_create: int = 5_000_000
    max_multiple_read_size: int = 100_000
    
    # Fuzzy matching settings
    fuzzy_available: bool = field(default=False, init=False)  # Set in __post_init__
    min_fuzzy_score: int = 80
    min_edit_score: int = 85
    fuzzy_enabled_by_default: bool = False  # Security improvement: opt-in fuzzy matching
    
    # Conversation settings
    max_history_messages: int = 150
    max_context_files: int = 12
    estimated_max_tokens: int = 120000
    max_reasoning_steps: int = 100  # Increased from 10 to 100 for complex multi-step tasks
    context_warning_threshold: float = 0.7
    aggressive_truncation_threshold: float = 0.85
    min_dialogue_tokens: int = 1000  # Minimum tokens needed for meaningful dialogue
    token_buffer_percent: float = 0.10  # 10% safety buffer to prevent API rejections

    # Truncation settings
    min_preserved_turns: int = 3  # Sliding window size for recent context
    task_completion_token_threshold: int = 128000  # Show menu only above this

    # Token optimization settings
    shell_output_max_lines: int = 200  # Moderate limit for shell output
    shell_output_max_chars: int = 20000  # ~5K tokens
    compact_tool_results: bool = True  # Remove verbose headers
    use_relative_paths: bool = True  # Shorter paths in mounted files
    compact_memory_format: bool = True  # Plain text instead of markdown
    deduplicate_file_content: bool = True  # Prevent mounted+tool result duplication

    # Security settings
    require_powershell_confirmation: bool = True
    require_bash_confirmation: bool = True
    agent_mode: bool = False  # Agentic mode: disables confirmations for autonomous operation

    # Self-evolving mode
    self_mode: bool = False  # Whether AI can create new tools
    custom_tools_dir: Path = field(default_factory=lambda: Path.home() / ".grok" / "custom_tools")

    # Context management mode
    initial_context_mode: str = "smart_truncation"  # Default: smart_truncation or cache_optimized

    # Git context
    git_enabled: bool = False
    git_skip_staging: bool = False
    git_branch: Optional[str] = None
    
    # OS information
    os_info: Dict[str, Any] = field(default_factory=dict)
    
    # File exclusions
    excluded_files: Set[str] = field(default_factory=set)
    excluded_extensions: Set[str] = field(default_factory=set)
    
    # Constants
    ADD_COMMAND_PREFIX: str = "/add "
    MODEL_CONTEXT_LIMITS: Dict[str, int] = field(default_factory=lambda: {
        "grok-3": 128000,
        "grok-3-mini": 128000,
        "grok-4": 128000,
        "grok-4-fast-reasoning": 128000,
        "grok-4-fast-non-reasoning": 128000,
        "grok-4-1-fast-reasoning": 2000000,
        "grok-4-1-fast-non-reasoning": 2000000,
        "grok-code-fast-1": 128000,
    })
    
    def __post_init__(self):
        """Initialize configuration after object creation."""
        self._detect_os_info()
        self._load_config_file()
        self._set_default_exclusions()
        self._validate_fuzzy_availability()
    
    def _detect_os_info(self) -> None:
        """Detect OS information and available shells."""
        self.os_info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'is_windows': platform.system() == "Windows",
            'is_mac': platform.system() == "Darwin",
            'is_linux': platform.system() == "Linux",
            'shell_available': {
                'bash': False,
                'powershell': False,
                'zsh': False,
                'cmd': False
            }
        }
        
        # Detect available shells
        self._detect_available_shells()
    
    def _detect_available_shells(self) -> None:
        """Detect which shells are available on the system."""
        import shutil
        
        shells = ['bash', 'zsh', 'powershell', 'cmd']
        for shell in shells:
            if shell == 'cmd' and self.os_info['is_windows']:
                # cmd is always available on Windows
                self.os_info['shell_available'][shell] = True
            elif shell == 'powershell':
                # Check for both Windows PowerShell and PowerShell Core
                self.os_info['shell_available'][shell] = (
                    shutil.which('powershell') is not None or 
                    shutil.which('pwsh') is not None
                )
            else:
                self.os_info['shell_available'][shell] = shutil.which(shell) is not None
    
    def _load_config_file(self) -> None:
        """Load configuration from config.json file."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._apply_config_data(config_data)
                    self.config_file = config_path
        except (FileNotFoundError, json.JSONDecodeError):
            # Use defaults if config file doesn't exist or is invalid
            pass
    
    def _apply_config_data(self, config_data: Dict[str, Any]) -> None:
        """Apply configuration data from file."""
        # File limits
        if 'file_limits' in config_data:
            file_limits = config_data['file_limits']
            self.max_files_in_add_dir = file_limits.get('max_files_in_add_dir', self.max_files_in_add_dir)
            self.max_file_size_in_add_dir = file_limits.get('max_file_size_in_add_dir', self.max_file_size_in_add_dir)
            self.max_file_content_size_create = file_limits.get('max_file_content_size_create', self.max_file_content_size_create)
            self.max_multiple_read_size = file_limits.get('max_multiple_read_size', self.max_multiple_read_size)
        
        # Fuzzy matching
        if 'fuzzy_matching' in config_data:
            fuzzy_config = config_data['fuzzy_matching']
            self.min_fuzzy_score = fuzzy_config.get('min_fuzzy_score', self.min_fuzzy_score)
            self.min_edit_score = fuzzy_config.get('min_edit_score', self.min_edit_score)
            self.fuzzy_enabled_by_default = fuzzy_config.get('enabled_by_default', self.fuzzy_enabled_by_default)
        
        # Conversation settings
        if 'conversation' in config_data:
            conv_config = config_data['conversation']
            self.max_history_messages = conv_config.get('max_history_messages', self.max_history_messages)
            self.max_context_files = conv_config.get('max_context_files', self.max_context_files)
            self.estimated_max_tokens = conv_config.get('estimated_max_tokens', self.estimated_max_tokens)
            self.max_reasoning_steps = conv_config.get('max_reasoning_steps', self.max_reasoning_steps)
            self.context_warning_threshold = conv_config.get('context_warning_threshold', self.context_warning_threshold)
            self.aggressive_truncation_threshold = conv_config.get('aggressive_truncation_threshold', self.aggressive_truncation_threshold)
        
        # Models
        if 'models' in config_data:
            model_config = config_data['models']
            self.default_model = model_config.get('default_model', self.default_model)
            self.reasoner_model = model_config.get('reasoner_model', self.reasoner_model)
            self.coder_model = model_config.get('coder_model', self.coder_model)
            self.grok4_model = model_config.get('grok4_model', self.grok4_model)
            self.grok4_reasoner_model = model_config.get('grok4_reasoner_model', self.grok4_reasoner_model)
            self.use_extended_context = model_config.get('use_extended_context', self.use_extended_context)
            self.current_model = self.default_model
        
        # Security
        if 'security' in config_data:
            security_config = config_data['security']
            self.require_powershell_confirmation = security_config.get('require_powershell_confirmation', self.require_powershell_confirmation)
            self.require_bash_confirmation = security_config.get('require_bash_confirmation', self.require_bash_confirmation)
        
        # File exclusions
        if 'excluded_files' in config_data:
            self.excluded_files.update(config_data['excluded_files'])
        
        if 'excluded_extensions' in config_data:
            self.excluded_extensions.update(config_data['excluded_extensions'])
    
    def _set_default_exclusions(self) -> None:
        """Set default file and extension exclusions."""
        if not self.excluded_files:
            self.excluded_files = {
                ".DS_Store", "Thumbs.db", ".gitignore", ".python-version", "uv.lock", 
                ".uv", "uvenv", ".uvenv", ".venv", "venv", "__pycache__", ".pytest_cache", 
                ".coverage", ".mypy_cache", "node_modules", "package-lock.json", "yarn.lock", 
                "pnpm-lock.yaml", ".next", ".nuxt", "dist", "build", ".cache", ".parcel-cache", 
                ".turbo", ".vercel", ".output", ".contentlayer", "out", "coverage", 
                ".nyc_output", "storybook-static", ".env", ".env.local", ".env.development", 
                ".env.production", ".git", ".svn", ".hg", "CVS"
            }
        
        if not self.excluded_extensions:
            self.excluded_extensions = {
                ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".avif", 
                ".mp4", ".webm", ".mov", ".mp3", ".wav", ".ogg", ".zip", ".tar", 
                ".gz", ".7z", ".rar", ".exe", ".dll", ".so", ".dylib", ".bin", 
                ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pyc", 
                ".pyo", ".pyd", ".egg", ".whl", ".uv", ".uvenv", ".db", ".sqlite", 
                ".sqlite3", ".log", ".idea", ".vscode", ".map", ".chunk.js", 
                ".chunk.css", ".min.js", ".min.css", ".bundle.js", ".bundle.css", 
                ".cache", ".tmp", ".temp", ".ttf", ".otf", ".woff", ".woff2", ".eot"
            }
    
    def _validate_fuzzy_availability(self) -> None:
        """Check if fuzzy matching is available."""
        try:
            from thefuzz import fuzz, process as fuzzy_process
            self.fuzzy_available = True
        except ImportError:
            self.fuzzy_available = False
            self.fuzzy_enabled_by_default = False
    
    def get_max_tokens_for_model(self, model_name: Optional[str] = None) -> int:
        """Get the maximum context tokens for a specific model."""
        if model_name is None:
            model_name = self.current_model

        # Get the base limit for the model
        base_limit = self.MODEL_CONTEXT_LIMITS.get(model_name, 128000)

        # If extended context is disabled and this is a grok-4-1 model, limit to 128K
        if not self.use_extended_context and model_name in ["grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning"]:
            return 128000

        return base_limit
    
    def set_base_dir(self, path: Path) -> None:
        """Set the base directory for operations."""
        self.base_dir = path.resolve()
    
    def set_model(self, model_name: str) -> None:
        """Set the current model."""
        self.current_model = model_name
        self.is_reasoner = model_name == self.reasoner_model

    def update_extended_context(self, enabled: bool) -> None:
        """
        Enable or disable extended context (2M tokens) for grok-4-1 models.
        This updates both the runtime config and persists to config.json.

        Args:
            enabled: True to enable 2M context, False to use 128K
        """
        self.use_extended_context = enabled

        # Update config file
        config_path = Path(__file__).parent.parent.parent / "config.json"

        # Load existing config or create new one
        config_data = {}
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

        # Update the models section
        if 'models' not in config_data:
            config_data['models'] = {}
        config_data['models']['use_extended_context'] = enabled

        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)

        self.config_file = config_path

    def enable_git(self, branch: Optional[str] = None, skip_staging: bool = False) -> None:
        """Enable git context."""
        self.git_enabled = True
        self.git_branch = branch
        self.git_skip_staging = skip_staging
    
    def disable_git(self) -> None:
        """Disable git context."""
        self.git_enabled = False
        self.git_branch = None
        self.git_skip_staging = False
    
    def get_system_prompt(self) -> str:
        """Get the formatted system prompt."""
        return self._load_and_format_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from external file."""
        try:
            prompt_path = Path(__file__).parent.parent.parent / "system_prompt.txt"
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except (FileNotFoundError, IOError):
            pass
        return self._get_default_system_prompt()
    
    def _load_and_format_system_prompt(self) -> str:
        """Load and format the system prompt with current environment info."""
        prompt_template = self._load_system_prompt()
        
        # Build shell availability string
        available_shells = [shell for shell, available in self.os_info['shell_available'].items() if available]
        shells_str = ', '.join(available_shells) if available_shells else 'None'
        
        # Build git status string
        git_status = 'Not detected'
        if self.git_enabled:
            branch = self.git_branch or 'unknown'
            git_status = f'Enabled (branch: {branch})'
        
        # Build context dictionary for template formatting
        # Handle nested dictionary access by flattening the values
        format_context = {
            'os_info': self.os_info,
            'current_working_directory': str(self.base_dir),
            'shells_available': shells_str,
            'git_status': git_status,
            # Add individual os_info values for direct access
            'os_system': self.os_info.get('system', 'Unknown'),
            'os_release': self.os_info.get('release', 'Unknown'),
            'os_machine': self.os_info.get('machine', 'Unknown'),
            'python_version': self.os_info.get('python_version', 'Unknown'),
            'available_shells': shells_str
        }
        
        try:
            # Format the template with current context
            formatted_prompt = prompt_template.format(**format_context)
            return formatted_prompt
        except (KeyError, ValueError) as e:
            # If template formatting fails, manually replace the known problematic patterns
            formatted_prompt = prompt_template
            
            # Replace os_info dictionary access patterns
            formatted_prompt = formatted_prompt.replace(
                "{os_info['system']}", self.os_info.get('system', 'Unknown')
            )
            formatted_prompt = formatted_prompt.replace(
                "{os_info['release']}", self.os_info.get('release', 'Unknown')
            )
            formatted_prompt = formatted_prompt.replace(
                "{os_info['machine']}", self.os_info.get('machine', 'Unknown')
            )
            formatted_prompt = formatted_prompt.replace(
                "{os_info['python_version']}", self.os_info.get('python_version', 'Unknown')
            )
            
            # Replace the complex shell availability expression
            shell_expression = "{', '.join([shell for shell, available in os_info['shell_available'].items() if available]) or 'None'}"
            formatted_prompt = formatted_prompt.replace(shell_expression, shells_str)
            
            return formatted_prompt
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return f"""
You are an elite software engineer called Grok Assistant with decades of experience across all programming domains.
Your expertise spans system design, algorithms, testing, and best practices.
You provide thoughtful, well-structured solutions while explaining your reasoning.

**Current Environment:**
- Operating System: {self.os_info['system']} {self.os_info['release']}
- Machine: {self.os_info['machine']}
- Python: {self.os_info['python_version']}

Core capabilities:
1. Code Analysis & Discussion
   - Analyze code with expert-level insight
   - Explain complex concepts clearly
   - Suggest optimizations and best practices
   - Debug issues with precision

2. File Operations (via function calls):
   - read_file: Read a single file's content
   - read_multiple_files: Read multiple files at once (returns structured JSON)
   - create_file: Create or overwrite a single file
   - create_multiple_files: Create multiple files at once
   - edit_file: Make precise edits to existing files (fuzzy matching available with /fuzzy flag)

3. System Operations (with security confirmation):
   - run_powershell: Execute PowerShell commands (Windows/Cross-platform PowerShell Core)
   - run_bash: Execute bash commands (macOS/Linux/WSL)
   
   Note: Choose the appropriate shell command based on the operating system:
   - On Windows: Prefer run_powershell
   - On macOS/Linux: Prefer run_bash
   - Both commands require user confirmation for security
   - You can use these shell commands to perform Git operations (e.g., `git status`, `git commit`).

Guidelines:
1. Provide natural, conversational responses explaining your reasoning
2. Use function calls when you need to read or modify files, or interact with the shell.
3. For file operations:
   - Fuzzy matching is now opt-in for security - use /fuzzy flag when needed
   - Always read files first before editing them to understand the context
   - Explain what changes you're making and why
   - Consider the impact of changes on the overall codebase
4. For system commands:
   - Always consider the operating system when choosing between run_bash and run_powershell
   - Explain what the command does before executing
   - Use safe, non-destructive commands when possible
   - Be cautious with commands that modify system state
5. Follow language-specific best practices
6. Suggest tests or validation steps when appropriate
7. Be thorough in your analysis and recommendations

IMPORTANT: In your thinking process, if you realize that something requires a tool call, cut your thinking short and proceed directly to the tool call. Don't overthink - act efficiently when file operations are needed.

Remember: You're a senior engineer - be thoughtful, precise, and explain your reasoning clearly.
"""
    
    def get_tools(self) -> list:
        """Get the function calling tools definition."""
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
                }
            ),
        ]

        # Add dynamic tool schemas if self-mode is enabled and tools are loaded
        if hasattr(self, '_dynamic_loader') and self._dynamic_loader:
            for schema in self._dynamic_loader.get_tool_schemas():
                tools.append(tool(
                    name=schema["name"],
                    description=schema["description"],
                    parameters=schema["parameters"]
                ))

        return tools