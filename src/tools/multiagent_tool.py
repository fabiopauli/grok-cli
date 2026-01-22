#!/usr/bin/env python3

"""
Multi-Agent Coordination Tools

Implements role-based multi-agent decomposition with shared communication
via blackboard pattern.
"""

import atexit
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional
from filelock import FileLock

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..utils.logging_config import get_logger


class AgentRole:
    """Represents a specialized agent role."""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    TESTER = "tester"

    ROLE_PROMPTS = {
        PLANNER: """You are a PLANNING SPECIALIST agent. Your expertise is creating detailed, actionable plans.

**Your Core Responsibilities:**
- Break down complex goals into clear, sequential steps
- Identify dependencies between tasks
- Estimate complexity and suggest appropriate approaches
- Consider edge cases and potential risks
- Produce structured plans with clear success criteria

**Workflow:**
1. Analyze the goal thoroughly
2. Identify all sub-tasks and their relationships
3. Organize tasks in logical dependency order
4. Document assumptions and constraints
5. Provide clear deliverables for each step

**Output:** Your final result must be a structured plan posted to the blackboard.""",

        CODER: """You are a CODING SPECIALIST agent. Your expertise is implementing code changes efficiently and correctly.

**Your Core Responsibilities:**
- Implement features following specifications and plans
- Write clean, maintainable, well-documented code
- Follow project conventions and best practices
- Ensure code is syntactically correct before submitting
- Handle edge cases and error conditions

**Workflow:**
1. Read and understand existing code context
2. Implement changes incrementally
3. Verify syntax and basic functionality
4. Document complex logic with comments
5. Report implementation details and any challenges

**Output:** Your final result must include what was implemented and any important technical decisions.""",

        REVIEWER: """You are a CODE REVIEW SPECIALIST agent. Your expertise is ensuring code quality and security.

**Your Core Responsibilities:**
- Review code for correctness and style
- Identify potential bugs, security issues, and performance problems
- Suggest improvements and best practices
- Ensure code follows project conventions
- Provide constructive, actionable feedback

**Review Checklist:**
- Correctness: Does the code do what it's supposed to?
- Security: Are there vulnerabilities (injection, XSS, auth issues)?
- Performance: Are there obvious inefficiencies?
- Style: Does it follow project conventions?
- Maintainability: Is it readable and well-structured?

**Output:** Your final result must be a structured review with findings and recommendations.""",

        RESEARCHER: """You are a RESEARCH SPECIALIST agent. Your expertise is finding and analyzing information.

**Your Core Responsibilities:**
- Search codebases for relevant patterns and implementations
- Explore documentation and examples
- Identify best practices and common pitfalls
- Provide comprehensive context for decision-making
- Summarize findings clearly and concisely

**Research Strategy:**
1. Use grep_codebase for code patterns
2. Use inspect_code_structure for file overviews
3. Read relevant files for detailed understanding
4. Synthesize findings into actionable insights
5. Document sources and references

**Output:** Your final result must include key findings, relevant code locations, and recommendations.""",

        TESTER: """You are a TESTING SPECIALIST agent. Your expertise is ensuring code correctness through comprehensive testing.

**Your Core Responsibilities:**
- Design test cases covering normal and edge cases
- Write clear, maintainable test code
- Execute tests and report results
- Identify gaps in test coverage
- Suggest improvements for testability

**Testing Workflow:**
1. Understand what functionality needs testing
2. Design test cases (happy path, edge cases, error cases)
3. Write test code following project conventions
4. Execute tests and capture results
5. Report pass/fail status with details

**Output:** Your final result must include test coverage summary, pass/fail status, and any issues found."""
    }


class BlackboardCommunication:
    """
    Shared blackboard for multi-agent communication.

    Agents can read and write messages to the blackboard to coordinate.
    """

    def __init__(self, blackboard_path: Path):
        """
        Initialize blackboard.

        Args:
            blackboard_path: Path to blackboard JSON file
        """
        self.blackboard_path = blackboard_path
        self.lock_path = Path(str(blackboard_path) + ".lock")
        self.logger = get_logger("blackboard")

        # Initialize blackboard if it doesn't exist
        if not self.blackboard_path.exists():
            self._initialize_blackboard()

    def _initialize_blackboard(self) -> None:
        """Initialize empty blackboard."""
        data = {
            "created": time.time(),
            "messages": [],
            "shared_data": {}
        }
        self._write_blackboard(data)

    def _read_blackboard(self) -> dict:
        """Read blackboard data with file locking to prevent race conditions."""
        lock = FileLock(self.lock_path, timeout=10)
        try:
            with lock:
                with open(self.blackboard_path, encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._initialize_blackboard()
            return self._read_blackboard()

    def _write_blackboard(self, data: dict) -> None:
        """Write blackboard data with file locking to prevent race conditions."""
        lock = FileLock(self.lock_path, timeout=10)
        with lock:
            with open(self.blackboard_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def post_message(self, agent_id: str, message: str, message_type: str = "info") -> None:
        """
        Post a message to the blackboard.

        Args:
            agent_id: ID of the agent posting
            message: Message content
            message_type: Type of message (info, request, result, error)
        """
        data = self._read_blackboard()

        data["messages"].append({
            "timestamp": time.time(),
            "agent_id": agent_id,
            "type": message_type,
            "content": message
        })

        self._write_blackboard(data)
        self.logger.debug(f"Agent {agent_id} posted message: {message[:50]}...")

    def get_messages(
        self, since: Optional[float] = None, message_type: Optional[str] = None
    ) -> list[dict]:
        """
        Get messages from blackboard.

        Args:
            since: Only get messages after this timestamp
            message_type: Filter by message type

        Returns:
            List of messages
        """
        data = self._read_blackboard()
        messages = data.get("messages", [])

        if since is not None:
            messages = [m for m in messages if m["timestamp"] > since]

        if message_type is not None:
            messages = [m for m in messages if m["type"] == message_type]

        return messages

    def set_shared_data(self, key: str, value: Any) -> None:
        """Set shared data on the blackboard."""
        data = self._read_blackboard()
        data["shared_data"][key] = value
        self._write_blackboard(data)

    def get_shared_data(self, key: str, default: Any = None) -> Any:
        """Get shared data from the blackboard."""
        data = self._read_blackboard()
        return data.get("shared_data", {}).get(key, default)

    def clear(self) -> None:
        """Clear the blackboard."""
        self._initialize_blackboard()


class SpawnAgentTool(BaseTool):
    """
    Tool for spawning specialized agent instances.

    Spawns new grok-cli instances with role-specific prompts
    that communicate via shared blackboard.
    """

    # Class-level registry for process cleanup
    _process_registry = []
    _cleanup_registered = False

    def __init__(self, config: Config):
        """
        Initialize spawn agent tool.

        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.logger = get_logger("spawn_agent")
        self.active_agents = {}

        # Setup blackboard
        self.blackboard_path = config.base_dir / ".grok_blackboard.json"
        self.blackboard = BlackboardCommunication(self.blackboard_path)

        # Register cleanup handlers (only once)
        if not SpawnAgentTool._cleanup_registered:
            atexit.register(SpawnAgentTool._cleanup_all_processes)
            signal.signal(signal.SIGTERM, SpawnAgentTool._signal_handler)
            signal.signal(signal.SIGINT, SpawnAgentTool._signal_handler)
            SpawnAgentTool._cleanup_registered = True

    @classmethod
    def _cleanup_all_processes(cls):
        """Cleanup all spawned agent processes."""
        logger = get_logger("spawn_agent")
        if cls._process_registry:
            logger.info(f"Cleaning up {len(cls._process_registry)} spawned agent processes...")
            for process in cls._process_registry:
                try:
                    if process.poll() is None:  # Process still running
                        logger.debug(f"Terminating agent process PID {process.pid}")
                        process.terminate()
                        # Give it 2 seconds to terminate gracefully
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            logger.warning(f"Force killing agent process PID {process.pid}")
                            process.kill()
                except Exception as e:
                    logger.error(f"Error cleaning up process: {e}")
            cls._process_registry.clear()

    @classmethod
    def _signal_handler(cls, signum, frame):
        """Handle termination signals by cleaning up processes."""
        logger = get_logger("spawn_agent")
        logger.info(f"Received signal {signum}, cleaning up agent processes...")
        cls._cleanup_all_processes()
        # Re-raise the signal to allow normal termination
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)

    @classmethod
    def cleanup_finished_processes(cls):
        """Remove finished processes from the registry."""
        cls._process_registry = [p for p in cls._process_registry if p.poll() is None]

    def get_name(self) -> str:
        """Get the tool name."""
        return "spawn_agent"

    @property
    def description(self) -> str:
        return "Spawn a specialized agent instance with a specific role (planner, coder, reviewer, researcher, tester). Agents communicate via shared blackboard."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": ["planner", "coder", "reviewer", "researcher", "tester"],
                    "description": "The specialized role for this agent"
                },
                "task": {
                    "type": "string",
                    "description": "The specific task for this agent to complete"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context or information for the agent"
                },
                "background": {
                    "type": "boolean",
                    "description": "Run agent in background (default: true)",
                    "default": True
                }
            },
            "required": ["role", "task"]
        }

    def execute(self, **kwargs) -> ToolResult:
        """
        Spawn a specialized agent.

        Args:
            role: Agent role
            task: Task for the agent
            context: Additional context (optional)
            background: Run in background (default: True)

        Returns:
            ToolResult with agent information
        """
        role = kwargs.get("role")
        task = kwargs.get("task")
        context = kwargs.get("context", "")
        run_background = kwargs.get("background", True)

        if role not in AgentRole.ROLE_PROMPTS:
            return self.error(f"Invalid role: {role}")

        # Generate agent ID
        agent_id = f"{role}_{int(time.time())}"

        # Create agent prompt
        agent_prompt = self._create_agent_prompt(role, task, context, agent_id)

        # Spawn agent subprocess
        try:
            if run_background:
                agent_process = self._spawn_background_agent(agent_id, agent_prompt)
                self.active_agents[agent_id] = {
                    "process": agent_process,
                    "role": role,
                    "task": task,
                    "started": time.time()
                }

                # Post to blackboard
                self.blackboard.post_message(
                    "coordinator",
                    f"Spawned {role} agent {agent_id} for task: {task}",
                    "info"
                )

                return self.success(f"SPAWN_AGENT_ID: {agent_id}")
            else:
                # Run synchronously
                result = self._spawn_foreground_agent(agent_id, agent_prompt)
                return self.success(
                    f"{role.title()} agent completed:\n\n{result}"
                )

        except Exception as e:
            self.logger.error(f"Error spawning agent: {e}")
            return self.error(f"Failed to spawn agent: {str(e)}")

    def _create_agent_prompt(self, role: str, task: str, context: str, agent_id: str) -> str:
        """Create prompt for agent with comprehensive role guidance."""
        role_prompt = AgentRole.ROLE_PROMPTS.get(role, "")

        prompt = f"""{role_prompt}

**AGENT SESSION INFO:**
- Agent ID: {agent_id}
- Role: {role.upper()}
- Assigned Task: {task}
"""
        if context:
            prompt += f"- Additional Context: {context}\n"

        prompt += f"""
**CRITICAL INSTRUCTIONS:**
1. **Stay Focused:** Execute ONLY your assigned task. Do not deviate or take on additional work.
2. **Be Autonomous:** You have full access to tools. Read files, execute commands, make changes as needed.
3. **Communicate Progress:** Use write_to_blackboard to share important updates and findings.
4. **Report Completion:** When finished, use write_to_blackboard with message_type='result' to report your final outcome.
5. **Be Efficient:** Complete your task in the minimum number of steps. Avoid over-engineering.
6. **Handle Errors:** If you encounter errors, attempt to resolve them. If unable to proceed, report the blocker.

**BLACKBOARD COMMUNICATION:**
- Location: {self.blackboard_path}
- Your agent ID: {agent_id}
- Post updates: write_to_blackboard(message="update text", message_type="info")
- Post results: write_to_blackboard(message="final result", message_type="result")
- Read others: read_blackboard() to see messages from coordinator or other agents

**TASK EXECUTION:**
Begin your task immediately. Work methodically and report your final result when complete.
"""

        return prompt

    def _spawn_background_agent(self, agent_id: str, prompt: str) -> subprocess.Popen:
        """Spawn agent in background using main.py CLI entrypoint."""
        # Save prompt to file for debugging
        prompt_file = self.config.base_dir / f".agent_prompt_{agent_id}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        # CORRECT CLI command for grok-cli
        cmd = [
            sys.executable, "main.py",
            "--agent",           # Autonomous agent mode
            "--max-steps", "20", # Safety limit
            prompt               # Agent task prompt
        ]

        process = subprocess.Popen(
            cmd,
            cwd=str(self.config.base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Register process for cleanup
        SpawnAgentTool._process_registry.append(process)

        self.logger.info(f"✅ Spawned {agent_id} (PID: {process.pid}) with cmd: python main.py --agent")
        return process

    def _spawn_foreground_agent(self, agent_id: str, prompt: str) -> str:
        """Spawn agent in foreground and wait for result."""
        # Save prompt to file for debugging
        prompt_file = self.config.base_dir / f".agent_prompt_{agent_id}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        # Command for grok-cli
        cmd = [
            sys.executable, "main.py",
            "--agent",           # Autonomous agent mode
            "--max-steps", "20", # Safety limit
            prompt               # Agent task prompt
        ]

        # Run synchronously and wait for completion
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.config.base_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # After completion, check blackboard for results
            messages = self.blackboard.get_messages(message_type="result")
            agent_results = [m for m in messages if m["agent_id"] == agent_id]

            if agent_results:
                # Return the latest result from this agent
                latest_result = max(agent_results, key=lambda m: m["timestamp"])
                return latest_result["content"]
            else:
                # Return stdout if no blackboard result
                output = result.stdout.strip()
                if output:
                    return output
                elif result.stderr:
                    return f"Agent completed with errors:\n{result.stderr}"
                else:
                    return "Agent completed but no result found on blackboard."

        except subprocess.TimeoutExpired:
            return "Agent execution timed out after 5 minutes."
        except Exception as e:
            return f"Error running foreground agent: {str(e)}"


class ReadBlackboardTool(BaseTool):
    """Tool for reading messages from the shared blackboard."""

    def __init__(self, config: Config):
        """Initialize read blackboard tool."""
        super().__init__(config)
        self.blackboard_path = config.base_dir / ".grok_blackboard.json"
        self.blackboard = BlackboardCommunication(self.blackboard_path)
        self.last_read_time = 0

    def get_name(self) -> str:
        """Get the tool name."""
        return "read_blackboard"

    @property
    def description(self) -> str:
        return "Read messages from the shared agent blackboard. Use this to monitor spawned agents and receive their results."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "enum": ["info", "request", "result", "error"],
                    "description": "Filter messages by type (optional)"
                },
                "new_only": {
                    "type": "boolean",
                    "description": "Only read new messages since last read",
                    "default": True
                }
            }
        }

    def execute(self, **kwargs) -> ToolResult:
        """Read messages from blackboard."""
        message_type = kwargs.get("message_type")
        new_only = kwargs.get("new_only", True)

        since = self.last_read_time if new_only else None
        messages = self.blackboard.get_messages(since=since, message_type=message_type)

        # Update last read time
        self.last_read_time = time.time()

        if not messages:
            return self.success("No new messages on the blackboard.")

        # Format messages
        output_lines = [f"Blackboard messages ({len(messages)} total):"]
        for msg in messages:
            timestamp = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
            agent_id = msg["agent_id"]
            msg_type = msg["type"]
            content = msg["content"]

            output_lines.append(f"\n[{timestamp}] {agent_id} ({msg_type}): {content}")

        return self.success("\n".join(output_lines))


class WriteBlackboardTool(BaseTool):
    """Tool for writing messages to the shared blackboard."""

    def __init__(self, config: Config):
        """Initialize write blackboard tool."""
        super().__init__(config)
        self.blackboard_path = config.base_dir / ".grok_blackboard.json"
        self.blackboard = BlackboardCommunication(self.blackboard_path)

    def get_name(self) -> str:
        """Get the tool name."""
        return "write_to_blackboard"

    @property
    def description(self) -> str:
        return "Write a message to the shared agent blackboard. Use this to communicate with other agents or report results."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to write"
                },
                "message_type": {
                    "type": "string",
                    "enum": ["info", "request", "result", "error"],
                    "description": "Type of message",
                    "default": "info"
                }
            },
            "required": ["message"]
        }

    def execute(self, **kwargs) -> ToolResult:
        """Write message to blackboard."""
        message = kwargs.get("message")
        message_type = kwargs.get("message_type", "info")

        if not message:
            return self.error("Message is required")

        # Use "coordinator" as agent ID for main agent
        agent_id = getattr(self.config, '_agent_id', 'coordinator')

        self.blackboard.post_message(agent_id, message, message_type)

        return self.success(f"Posted {message_type} message to blackboard")


def create_multiagent_tools(config: Config) -> list[BaseTool]:
    """
    Create multi-agent coordination tools.

    Args:
        config: Configuration object

    Returns:
        List of multi-agent tools
    """
    return [
        SpawnAgentTool(config),
        ReadBlackboardTool(config),
        WriteBlackboardTool(config)
    ]
