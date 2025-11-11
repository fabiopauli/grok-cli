# Grok CLI

A powerful command-line AI assistant built with modular architecture and xAI's Grok models. Features intelligent context management, secure tool execution, and a rich console interface.

## Features

- **Dual AI Models**: Switch between Grok-4-Fast-Non-Reasoning (default) and Grok-4-Fast-Reasoning (enhanced reasoning)
- **Intelligent File Operations**: Read, create, and edit files with optional fuzzy matching
- **Secure Shell Execution**: Cross-platform shell commands with user confirmation
- **Smart Context Management**: Automatic conversation truncation with token estimation
- **Rich Console Interface**: Beautiful formatting with syntax highlighting
- **Modular Architecture**: Clean separation of concerns with dependency injection
- **Comprehensive Testing**: Full test suite with pytest

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

## Usage

### Basic Usage

Start the interactive assistant:

```bash
# Using uv
uv run main.py

# Using python directly
python main.py
```

### Available Commands

- `/add <file_pattern>` - Add files to conversation context
- `/context` - Show current conversation context and token usage
- `/reasoner` or `/r` - Switch to Grok-4-Fast-Reasoning for enhanced reasoning (temporary)
- `/fuzzy` - Enable fuzzy file/code matching for current session
- `/exit` or `/quit` - Exit the application
- `Ctrl+C` - Exit the application

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

1. **Dependency Injection**: Configuration passed to all components
2. **Modular Design**: Clear separation of concerns
3. **Security-First**: Shell commands require confirmation
4. **Context Management**: Intelligent conversation truncation
5. **Cross-Platform**: Works on Windows, macOS, and Linux

## Security Features

- **Shell Command Confirmation**: All shell operations require user approval
- **Path Validation**: Robust file path sanitization
- **File Size Limits**: Configurable limits for file operations
- **Exclusion Patterns**: Automatically excludes system files
- **Fuzzy Matching**: Opt-in only for security

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