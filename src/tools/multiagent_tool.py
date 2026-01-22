#!/usr/bin/env python3

"""
Multi-Agent Coordination Tools

Implements role-based multi-agent decomposition with shared communication
via blackboard pattern.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

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
        PLANNER: "You are a planning agent. Create detailed step-by-step plans for coding tasks. Focus on breaking down complex tasks into manageable steps.",
        CODER: "You are a coding agent. Implement code changes based on provided plans. Focus on writing clean, correct code.",
        REVIEWER: "You are a code review agent. Review code changes for correctness, style, and potential issues. Provide constructive feedback.",
        RESEARCHER: "You are a research agent. Search codebases and documentation to find relevant information. Focus on thorough exploration.",
        TESTER: "You are a testing agent. Write and run tests to verify code correctness. Focus on comprehensive test coverage."
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
        """Read blackboard data."""
        try:
            with open(self.blackboard_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._initialize_blackboard()
            return self._read_blackboard()

    def _write_blackboard(self, data: dict) -> None:
        """Write blackboard data."""
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

    @property
    def name(self) -> str:
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

                return self.success(
                    f"Spawned {role} agent {agent_id} in background.\n"
                    f"Task: {task}\n\n"
                    f"Use read_blackboard tool to monitor agent progress.\n"
                    f"Agent will communicate results via the shared blackboard."
                )
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
        """Create prompt for agent."""
        role_prompt = AgentRole.ROLE_PROMPTS.get(role, "")

        prompt = f"""{role_prompt}

Your ID: {agent_id}
Your task: {task}
"""
        if context:
            prompt += f"\nContext: {context}"

        prompt += f"""

IMPORTANT:
- Focus ONLY on your assigned task
- Use the write_to_blackboard tool to share your results
- Keep your actions concise and focused
- When complete, write your final result to the blackboard with type 'result'

Blackboard file: {self.blackboard_path}

Begin your task now."""

        return prompt

    def _spawn_background_agent(self, agent_id: str, prompt: str) -> subprocess.Popen:
        """Spawn agent in background."""
        # Create temporary file for prompt
        prompt_file = self.config.base_dir / f".agent_prompt_{agent_id}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        # Spawn grok-cli subprocess
        cmd = [
            "python", "-m", "grok_cli",
            "--agent",  # Enable autonomous mode
            "--max-steps", "20",  # Limit steps to prevent runaway
            prompt
        ]

        process = subprocess.Popen(
            cmd,
            cwd=str(self.config.base_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        self.logger.info(f"Spawned background agent {agent_id} (PID: {process.pid})")
        return process

    def _spawn_foreground_agent(self, agent_id: str, prompt: str) -> str:
        """Spawn agent in foreground and wait for result."""
        # For foreground, we would integrate with the main session
        # For now, return a placeholder
        return f"Foreground agent execution not yet implemented. Use background=true."


class ReadBlackboardTool(BaseTool):
    """Tool for reading messages from the shared blackboard."""

    def __init__(self, config: Config):
        """Initialize read blackboard tool."""
        super().__init__(config)
        self.blackboard_path = config.base_dir / ".grok_blackboard.json"
        self.blackboard = BlackboardCommunication(self.blackboard_path)
        self.last_read_time = 0

    @property
    def name(self) -> str:
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

    @property
    def name(self) -> str:
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
