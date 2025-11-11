# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
- **Main entry point**: `uv run main.py` or `python main.py`
- **Development setup**: `uv sync` (installs dependencies from pyproject.toml)
- **Alternative setup**: `pip install -r requirements.txt`

### Testing
- **Run tests**: `pytest` or `uv run pytest`
- **Test files located in**: `tests/` directory with comprehensive test structure
- **Test configuration**: Uses pytest (>=8.4.1) as defined in pyproject.toml

### Environment Setup
- **Required**: Set `XAI_API_KEY` environment variable (create `.env` file or export)
- **Python version**: Requires Python 3.11+
- **Package manager**: Uses `uv` for dependency management (recommended) or pip

## Architecture Overview

### Core Design Pattern
This is a modular AI assistant built with strict separation of concerns and dependency injection. The architecture eliminates global state and uses clear component boundaries.

### Key Components

**Main Orchestrator** (`main.py`):
- Thin coordinator that initializes all components
- Handles main application loop and user input processing
- Manages tool call execution and AI responses

**Core Layer** (`src/core/`):
- `config.py`: Centralized configuration with environment detection, model settings, and security controls
- `session.py`: Session management with conversation state, context management, and model switching

**Command Layer** (`src/commands/`):
- Handles special commands like `/add`, `/git`, `/reasoner`, `/context`
- Each command type has dedicated handlers (context, file, system commands)

**Tools Layer** (`src/tools/`):
- AI function calling implementations for file operations and shell commands
- Includes security confirmation for shell operations
- Supports fuzzy matching for file operations (opt-in)

**UI Layer** (`src/ui/`):
- Console interface with rich formatting
- Prompt management and user interaction
- Status indicators and error display

### Key Architecture Principles

1. **Dependency Injection**: Config object passed to all components, no global state
2. **Modular Design**: Each layer has specific responsibilities with clear interfaces
3. **Security-First**: Shell commands require confirmation, path validation, file size limits
4. **Context Management**: Intelligent conversation history truncation with token estimation
5. **Fuzzy Matching**: Optional fuzzy file/code matching using thefuzz library

### AI Integration Details

**Models**: Supports multiple xAI models:
- `grok-4-fast-non-reasoning`: Default conversational model
- `grok-4-fast-reasoning`: Enhanced reasoning model (can be used temporarily with `/r` command)
- `grok-code-fast-1`: Specialized code model (can be used with `/coder` command)

**Function Calling Tools**:
- `read_file`, `read_multiple_files`: File reading operations
- `create_file`, `create_multiple_files`: File creation
- `edit_file`: Precise code editing with optional fuzzy matching
- `run_bash`, `run_powershell`: Shell command execution (OS-aware)

### Context and Memory Management

The application automatically manages conversation context with:
- Token estimation using tiktoken
- Smart truncation preserving system prompts and recent context
- File context tracking (max 12 files)
- Warning thresholds at 70% and 85% token usage

### Security Features

- **Shell Command Confirmation**: All `run_bash`/`run_powershell` calls require user approval
- **Path Validation**: Robust file path sanitization
- **File Size Limits**: Configurable limits for file operations
- **Exclusion Patterns**: Automatically excludes system files, node_modules, etc.
- **Fuzzy Matching**: Opt-in only for security (use `/fuzzy` flag)

### Configuration System

Configuration is managed through:
- `config.py` with dataclass-based settings
- Optional `config.json` file for overrides
- Environment variable support (.env file)
- OS and shell detection for cross-platform compatibility

This codebase prioritizes security, modularity, and intelligent context management while providing a powerful AI-assisted development experience.