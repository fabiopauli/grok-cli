# Grok CLI

A powerful command-line AI assistant built with modular architecture and xAI's Grok models. Features intelligent context management, secure tool execution, and a rich console interface.

## Features

- **Self-Evolving AI**: AI can create custom tools at runtime with `/self` mode (saved to `~/.grok/custom_tools/`)
- **Multiple Grok Models**: Support for Grok 4.1 (2M context), legacy Grok 4, and specialized coding models
- **Extended Context Support**: Up to 2M tokens for Grok 4.1 models (defaults to 128K for cost optimization)
- **Agentic Mode**: Optional autonomous operation with `/agent` command (removes safety confirmations)
- **Advanced Editor Tools**: Diff-based patching (`apply_diff_patch`) alongside traditional search-replace editing
- **Smart Command Suggestions**: Fuzzy matching suggests corrections for typos in slash commands
- **Dual Context Modes**: Smart truncation (default) and cache-optimized modes for different use cases
- **Persistent Memory System**: Global and directory-specific memories that survive context truncations
- **Intelligent File Operations**: Read, create, and edit files with optional fuzzy matching
- **Secure Shell Execution**: Cross-platform shell commands with enhanced security patterns and user confirmation
- **Turn-Based Context Management**: Advanced conversation tracking with automatic summarization
- **Token Buffer Protection**: 10% safety buffer prevents API rejections at token limits
- **Rich Console Interface**: Beautiful formatting with syntax highlighting
- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Comprehensive Testing**: Full test suite with 238 tests and 91% pass rate

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- xAI API key

## Installation

### Option 1: Using uv (Recommended)

1. **Install uv** (if not already installed):
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone the repository**:
   ```bash
   git clone https://github.com/fabiopauli/grok-cli.git
   cd grok-cli
   ```

3. **Install dependencies**:
   ```bash
   uv sync
   ```

4. **Set up your API key**:
   ```bash
   # Create a .env file
   echo "XAI_API_KEY=your_api_key_here" > .env
   
   # Or export as environment variable
   export XAI_API_KEY=your_api_key_here
   ```

### Option 2: Using pip

1. **Clone the repository**:
   ```bash
   git clone https://github.com/fabiopauli/grok-cli.git
   cd grok-cli
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API key**:
   ```bash
   echo "XAI_API_KEY=your_api_key_here" > .env
   ```

## AI Models

The CLI supports multiple xAI Grok models:

### Grok 4.1 Models (Default)
- **grok-4-1-fast-non-reasoning** (default) - Fast conversational model with 2M token context
- **grok-4-1-fast-reasoning** - Enhanced reasoning model with 2M token context
- **Default context**: 128K tokens (cost-optimized)
- **Extended context**: 2M tokens (use `/max` command)

### Legacy Grok 4 Models
- **grok-4-fast-non-reasoning** - Legacy model with 128K context
- **grok-4-fast-reasoning** - Legacy reasoning model with 128K context

### Specialized Models
- **grok-code-fast-1** - Optimized for code generation and editing (128K context)

## Usage

The CLI supports two modes: **Interactive** (REPL) and **One-Shot** (single command execution).

### Interactive Mode (REPL)

Start the interactive assistant for a multi-turn conversation:

```bash
# Using uv (recommended)
uv run python main.py

# Using python directly
python main.py

# Start with reasoning model
uv run python main.py -r

# Start with agent mode enabled
uv run python main.py --agent

# Start with all options
uv run python main.py -r --max --agent
```

Once in interactive mode, you can:
- Chat naturally with the AI
- Use slash commands like `/help`, `/add`, `/agent`, etc.
- Switch models with `/reasoner`, `/coder`, `/default`
- Manage context with `/context`, `/clear`, `/max`

### One-Shot Mode (CLI)

Execute a single prompt and exit - perfect for scripts, automation, and quick queries:

```bash
# Basic one-shot query
uv run python main.py "create a Python script that explains recursion"

# Use reasoning model (short flag)
uv run python main.py -r "explain how quantum computing works"

# Use reasoning model (long flag)
uv run python main.py --reasoner "solve this complex problem"

# Enable extended 2M context
uv run python main.py --max "analyze this large codebase"

# Enable agent mode for autonomous operation
uv run python main.py --agent "setup a development environment"

# Combine multiple flags
uv run python main.py -r --max "comprehensive code analysis"
uv run python main.py --agent -r "autonomous refactoring task"
uv run python main.py --agent --max --reasoner "complex autonomous task"

# Control reasoning steps (tool call iterations)
uv run python main.py --max-steps 200 "complex multi-step task"
uv run python main.py --max-steps 0 "unlimited tool calls allowed"
uv run python main.py --agent --max-steps 0 "fully autonomous unlimited execution"

# Enable self-evolving mode
uv run python main.py --self "create a tool to analyze test coverage"
uv run python main.py --self --agent "create and test a database migration tool"
uv run python main.py --self -r "design a complex validation framework"
```

### Command-Line Options Reference

```
usage: main.py [-h] [-r] [--max] [--agent] [--self] [--max-steps N] [prompt]

Grok CLI - AI assistant powered by xAI

positional arguments:
  prompt          Prompt to execute (if not provided, starts interactive mode)

options:
  -h, --help      Show this help message and exit
  -r, --reasoner  Use the reasoning model (grok-4-1-fast-reasoning)
  --max           Enable extended 2M token context (Grok 4.1 models only)
  --agent         Enable agentic mode (autonomous shell execution without confirmations)
  --self          Enable self-evolving mode (AI can create custom tools)
  --max-steps N   Maximum reasoning steps (tool call iterations). Default: 100, use 0 for unlimited
```

**Flag Descriptions:**

- **`-r, --reasoner`**: Uses the reasoning model for enhanced analytical capabilities
  - Model: `grok-4-1-fast-reasoning`
  - Best for: Complex logic, math, detailed analysis
  - Can be toggled in interactive mode with `/reasoner` or `/r`

- **`--max`**: Enables full 2M token context for Grok 4.1 models
  - Default: 128K tokens (cost-optimized)
  - Extended: 2M tokens (higher cost)
  - Only works with Grok 4.1 models
  - Can be toggled in interactive mode with `/max`

- **`--agent`**: Disables shell command confirmations for autonomous operation
  - ⚠️ **Use with caution!** AI executes commands without asking
  - Best for: Trusted environments, automated workflows
  - Can be toggled in interactive mode with `/agent`
  - Security: Disabled by default

- **`--self`**: Enables self-evolving mode (AI can create custom tools)
  - 🧠 **Experimental!** AI can extend its own capabilities
  - Tools saved to `~/.grok/custom_tools/` and persist across sessions
  - AST validation blocks dangerous code (subprocess, eval, etc.)
  - Can be toggled in interactive mode with `/self`
  - Best for: Extending AI capabilities, creating project-specific tools
  - Security: Validated but minimal - review custom tools before production use

- **`--max-steps N`**: Sets maximum reasoning steps (tool call iterations)
  - Default: 100 steps (increased from legacy 10-step limit)
  - Use `0` or `unlimited` for unlimited tool calls
  - Prevents infinite loops while allowing complex multi-step tasks
  - Can be changed in interactive mode with `/max-steps [N]`
  - Example: `--max-steps 0` for unlimited, `--max-steps 200` for 200 steps

### Creating a Shell Alias (Optional)

For convenience, you can create an alias in your shell:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias grok='uv run python /path/to/grok-cli/main.py'

# Then use simply:
grok "your prompt here"
grok -r "complex question"
grok --agent "autonomous task"
```

### Using as a CLI Tool in Scripts

The one-shot mode is perfect for shell scripts, automation, and CI/CD pipelines:

```bash
#!/bin/bash

# Generate documentation
uv run python main.py "generate API documentation for src/api.py" > docs/api.md

# Code review automation
REVIEW=$(uv run python main.py -r "review this pull request for security issues: $(git diff main)")
echo "$REVIEW" | mail -s "Code Review" team@example.com

# Automated refactoring
uv run python main.py --agent "refactor all Python files to use type hints"

# Generate commit messages
COMMIT_MSG=$(uv run python main.py "write a concise commit message for: $(git diff --staged)")
git commit -m "$COMMIT_MSG"

# CI/CD integration
if uv run python main.py -r "analyze if this code change is safe to deploy: $(git diff)"; then
    echo "Deploying..."
    ./deploy.sh
fi
```

**Benefits of CLI mode:**
- ✅ **Scriptable**: Integrate AI into bash scripts, Makefiles, CI/CD
- ✅ **Fast**: No interactive overhead, immediate results
- ✅ **Pipeable**: Works with Unix pipes and redirects
- ✅ **Automatable**: Perfect for cron jobs and automated workflows
- ✅ **Stateless**: Each invocation is independent

### Available Commands

#### Model Switching
- `/r` or `/reasoner` - Toggle between default and reasoning model (Grok 4.1)
- `/default` - Switch back to default model
- `/coder` - Switch to specialized coding model (grok-code-fast-1)
- `/grok-4` - Switch to legacy Grok 4 model
- `/4r` - Switch to legacy Grok 4 reasoning model

#### Context Management
- `/context` - Show context usage statistics
- `/context-mode` - Show current context management mode and options
- `/sequential` - Switch to cache-optimized context mode
- `/smart` - Switch to smart truncation mode (default)
- `/max` - Enable 2M token context for Grok 4.1 models
- `/clear` - Clear conversation context

#### File Operations
- `/add <file_pattern>` - Add files to conversation context
- `/fuzzy` - Enable fuzzy file/code matching for current session

#### System Commands
- `/agent` - Toggle agentic mode (autonomous shell execution without confirmations)
- `/self` - Toggle self-evolving mode (AI can create custom tools)
- `/reload-tools` - Reload custom tools from ~/.grok/custom_tools/
- `/max-steps [N]` - Set maximum reasoning steps (default: 100, use 0 or unlimited for no limit)
- `/jobs` - List all background jobs with status and runtime
- `/help` - Show available commands
- `/exit` or `/quit` - Exit the application

#### Interrupt Control
- **`Ctrl+C`** - Interrupt current operation (tool execution, long command)
  - First press: Stops current operation, returns to prompt
  - Second press: Exits application
  - Works during tool calls and AI responses

#### Command Suggestions
If you type an unknown slash command, the CLI will suggest similar commands:
```
> /hlep
⚠️  Unknown command. Did you mean '/help'? (y/N):
```

### Example Session

```
$ uv run main.py
Welcome to Grok Assistant!
Type your questions or commands. Use /help for available commands.

> /add src/core/*.py
Added 2 files to context: config.py, session.py

> Explain the configuration system
The configuration system is built around a dataclass-based approach...

> /r How can I optimize the token estimation?
[Switches to Grok-4-Fast-Reasoning for enhanced reasoning]
To optimize token estimation, consider these approaches...

> /hlep
⚠️  Unknown command. Did you mean '/help'? (y/N): y
[Shows help menu]

> /agent
⚡ Agentic mode enabled
[AI can now execute shell commands without asking]
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
XAI_API_KEY=your_api_key_here
```

### Optional Configuration File

Create `config.json` for advanced settings:

```json
{
  "model_name": "grok-4-fast-non-reasoning",
  "max_context_tokens": 100000,
  "file_size_limit": 1048576,
  "enable_fuzzy_matching": false
}
```

## Context Management

The CLI features intelligent context management with two modes:

### Smart Truncation Mode (Default)
- Automatically summarizes conversation at 70% token usage
- Keeps last 3 turns in full detail
- Older turns compressed into summaries
- Best for: Cost optimization, frequent API calls

### Cache-Optimized Mode
- Sequential context with periodic truncation at 90% usage
- Preserves full conversation history longer
- Best for: Long conversations, preserving history

Switch modes with `/sequential` or `/smart` commands.

### Extended Context (2M Tokens)

Grok 4.1 models support up to 2M tokens but default to 128K for cost efficiency:
- Use `/max` command to enable full 2M context
- Setting persists to config.json
- Note: Usage beyond 128K tokens is charged at a different rate

## Memory System

The CLI includes a persistent memory system:

### Global Memories
- Persist across all projects
- Stored in `~/.grok_global_memory.json`
- Use for user preferences, general patterns

### Directory Memories
- Project-specific memories
- Stored in `.grok_memory.json` per project
- Use for architectural decisions, project context

Memories are automatically injected into the system prompt and survive context truncations.

## Development

### Running Tests

```bash
# Using uv
uv run pytest

# Using pytest directly
pytest
```

### Project Structure

```
grok-cli/
├── main.py              # Application entry point
├── src/
│   ├── core/            # Core functionality
│   │   ├── config.py    # Configuration management
│   │   └── session.py   # Session and context management
│   ├── commands/        # Special command handlers
│   ├── tools/           # AI function calling tools
│   ├── ui/              # Console interface
│   └── utils/           # Utility functions
├── tests/               # Comprehensive test suite
├── pyproject.toml       # Project configuration
└── requirements.txt     # Pip dependencies
```

### Architecture Principles

1. **Dependency Injection**: Configuration passed to all components via AppContext composition root
2. **Modular Design**: Clear separation of concerns with focused components
3. **Self-Evolving Architecture**: Dynamic tool loading with AST-based validation
4. **Security-First**: Shell commands require confirmation by default, enhanced pattern detection, AST validation
5. **Turn-Based Context**: Conversations tracked as structured turns with automatic summarization
6. **Persistent Memory**: Global and directory-specific memories survive context truncations
7. **Dual-Mode Context**: Smart truncation (default) and cache-optimized modes
8. **Type Safety**: Pydantic models for runtime validation
9. **Token Buffer Protection**: 10% safety margin on all token calculations
10. **User-Friendly**: Command suggestions help prevent typos and discover features
11. **Cross-Platform**: Works on Windows, macOS, and Linux
12. **Comprehensive Testing**: 238 tests with 91% pass rate

## Security Features

- **Shell Command Confirmation**: All shell operations require user approval (unless `/agent` mode is enabled)
- **Enhanced Security Patterns**: Detects 60+ dangerous command patterns including:
  - Remote code execution (curl | bash, wget | sh)
  - Credential access (reading /etc/shadow, SSH keys, AWS credentials)
  - Destructive operations (rm -rf, git push --force, git reset --hard)
  - Code injection (python -c, perl -e, eval commands)
  - Obfuscation detection (excessive pipe/command chaining)
- **Security Audit Logging**: All dangerous commands logged (even in agent mode)
- **Agentic Mode**: Optional autonomous operation - disabled by default for safety
- **Self-Evolving Security**: AST validation for custom tools (blocks eval, exec, subprocess, etc.)
- **Command Validation**: Smart suggestions help prevent typos and unknown commands
- **Path Validation**: Robust file path sanitization
- **File Size Limits**: Configurable limits for file operations
- **Exclusion Patterns**: Automatically excludes system files
- **Fuzzy Matching**: Opt-in only for security
- **Token Buffer Protection**: 10% safety margin prevents API rejections

### Background Jobs

The CLI supports running long-running shell commands in the background, allowing you to continue interacting with the AI while tasks execute.

**How it works:**
1. AI uses `run_bash_background()` or `run_powershell_background()` to start a task
2. Returns immediately with a job ID
3. You can continue chatting with AI while job runs
4. AI can check job status with `check_background_job(job_id)`
5. View all jobs with `/jobs` command

**Example workflow:**
```
> Start a development server in the background and continue working

AI: I'll start the server in the background
[Uses run_bash_background("npm run dev")]
Background job started with ID: 1

> Now write tests for the API

AI: Sure, while the server runs in background (job 1)...
[Continues with test writing]

> Check if the server is running

AI: [Uses check_background_job(1)]
Job 1 is running. Output shows:
Server started on http://localhost:3000
```

**Background Job Management:**
- **View jobs**: `/jobs` - See all background jobs with status table
- **Check status**: AI uses `check_background_job(job_id)` to see output
- **List all**: AI uses `list_background_jobs()` for overview
- **Kill job**: AI uses `kill_background_job(job_id)` to stop

**Use cases:**
- Development servers (npm/yarn/python)
- Long-running builds or tests
- File watchers and monitors
- Database servers
- Any command you want to run while continuing work

### Agentic Mode

⚠️ **Use with caution!** Agentic mode allows the AI to execute shell commands without confirmation.

```bash
# Enable agent mode
> /agent
⚡ Agentic mode enabled
Shell commands will execute without confirmations.
⚠️  Warning: Use with caution - AI can now execute commands autonomously!

# Disable agent mode
> /agent
✓ Agentic mode disabled
Shell commands will require confirmation.
```

**When to use agent mode:**
- Fully autonomous workflows where you trust the AI
- Repetitive tasks requiring multiple shell commands
- Development environments with version control safety nets

**When NOT to use agent mode:**
- Production environments
- When executing unfamiliar operations
- Working with sensitive files or data

### Self-Evolving Mode

🧠 **Experimental Feature:** The AI can create custom tools that extend its capabilities permanently.

```bash
# Enable self-evolving mode
> /self
🔧 Self-evolving mode enabled
AI can now create new tools. Tools are saved to ~/.grok/custom_tools/
⚠️  Tools cannot modify the system prompt.

# Ask AI to create a tool
> Create a tool that analyzes code complexity

[AI creates and saves custom tool to ~/.grok/custom_tools/]
✓ Tool created successfully!

# Tool is immediately available and persists across sessions
> Use the complexity analyzer on src/core/config.py

[AI uses its own custom tool]

# Reload tools (if manually editing)
> /reload-tools
✓ Reloaded 3 custom tool(s)

# Disable self-mode
> /self
✓ Self-evolving mode disabled
```

**How it works:**
1. AI creates tools using the `create_tool()` function
2. Tool source code is validated for security (AST-based)
3. Tools are saved to `~/.grok/custom_tools/` directory
4. Tools are hot-loaded immediately and persist across restarts
5. AI can use its own tools in future conversations

**Safety features:**
- AST validation blocks dangerous imports (subprocess, eval, exec, pickle, ctypes)
- Blocks dangerous function calls (eval, exec, compile)
- Requires proper BaseTool structure
- All tool creation is logged
- Tools are user-reviewable in `~/.grok/custom_tools/`

**Use cases:**
- Create project-specific analysis tools
- Build custom formatters or validators
- Add domain-specific utilities
- Extend AI capabilities for your workflow

**Example tools AI can create:**
- Code complexity analyzers
- Custom linters or formatters
- Project documentation generators
- Database schema validators
- API endpoint mappers

⚠️ **Security note:** Review custom tools before using in production. The AI is trusted to create safe tools, but validation is minimal by design.

## API Key Setup

Get your xAI API key from [console.x.ai](https://console.x.ai) and either:

1. Add it to your `.env` file: `XAI_API_KEY=your_key_here`
2. Export as environment variable: `export XAI_API_KEY=your_key_here`
3. Pass it when running: `XAI_API_KEY=your_key_here uv run main.py`

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

## License

[License information - check LICENSE file]

## Support

For issues and questions, please open an issue on the [GitHub repository](https://github.com/fabiopauli/grok-cli/issues).