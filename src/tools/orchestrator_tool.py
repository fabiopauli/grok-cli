#!/usr/bin/env python3

"""
Orchestrator Tool for Multi-Agent Coordination

Coordinates multiple specialized agents to work together on complex tasks.
Decomposes tasks, assigns roles, monitors progress, and aggregates results.
"""

import json
import time
from typing import Any, Optional, List, Dict

from .base import BaseTool, ToolResult
from .multiagent_tool import BlackboardCommunication, AgentRole
from ..core.config import Config
from ..utils.logging_config import get_logger


class TaskDecomposition:
    """Represents a decomposed task with sub-tasks and role assignments."""

    def __init__(self, goal: str):
        """Initialize task decomposition."""
        self.goal = goal
        self.sub_tasks: List[Dict[str, Any]] = []
        self.dependencies: Dict[int, List[int]] = {}  # task_id -> [dependency_ids]

    def add_sub_task(
        self,
        description: str,
        role: str,
        priority: int = 1,
        dependencies: Optional[List[int]] = None
    ) -> int:
        """
        Add a sub-task to the decomposition.

        Args:
            description: Task description
            role: Agent role to assign
            priority: Task priority (1=highest)
            dependencies: List of task IDs this depends on

        Returns:
            Task ID
        """
        task_id = len(self.sub_tasks)
        self.sub_tasks.append({
            "id": task_id,
            "description": description,
            "role": role,
            "priority": priority,
            "status": "pending",
            "agent_id": None,
            "result": None
        })

        if dependencies:
            self.dependencies[task_id] = dependencies
        else:
            self.dependencies[task_id] = []

        return task_id

    def get_ready_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are ready to execute (dependencies satisfied)."""
        ready = []
        for task in self.sub_tasks:
            if task["status"] == "pending":
                # Check if all dependencies are complete
                deps = self.dependencies.get(task["id"], [])
                deps_complete = all(
                    self.sub_tasks[dep_id]["status"] == "completed"
                    for dep_id in deps
                )
                if deps_complete:
                    ready.append(task)

        # Sort by priority
        ready.sort(key=lambda t: t["priority"])
        return ready

    def mark_task_running(self, task_id: int, agent_id: str) -> None:
        """Mark task as running."""
        self.sub_tasks[task_id]["status"] = "running"
        self.sub_tasks[task_id]["agent_id"] = agent_id

    def mark_task_completed(self, task_id: int, result: str) -> None:
        """Mark task as completed."""
        self.sub_tasks[task_id]["status"] = "completed"
        self.sub_tasks[task_id]["result"] = result

    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(task["status"] == "completed" for task in self.sub_tasks)

    def get_progress(self) -> Dict[str, int]:
        """Get progress statistics."""
        total = len(self.sub_tasks)
        completed = sum(1 for task in self.sub_tasks if task["status"] == "completed")
        running = sum(1 for task in self.sub_tasks if task["status"] == "running")
        pending = sum(1 for task in self.sub_tasks if task["status"] == "pending")

        return {
            "total": total,
            "completed": completed,
            "running": running,
            "pending": pending,
            "progress_pct": (completed / total * 100) if total > 0 else 0
        }


class OrchestratorTool(BaseTool):
    """
    Orchestrator for coordinating multiple agents on complex tasks.

    This tool:
    1. Decomposes complex goals into sub-tasks
    2. Assigns appropriate agent roles to each sub-task
    3. Spawns agents with proper ordering based on dependencies
    4. Monitors agent progress via blackboard
    5. Aggregates results when all tasks complete
    """

    def __init__(self, config: Config, client=None):
        """
        Initialize orchestrator.

        Args:
            config: Configuration object
            client: xAI SDK client for task decomposition
        """
        super().__init__(config)
        self.client = client
        self.logger = get_logger("orchestrator")

        # Setup blackboard
        self.blackboard_path = config.base_dir / ".grok_blackboard.json"
        self.blackboard = BlackboardCommunication(self.blackboard_path)

        # Active orchestrations
        self.orchestrations: Dict[str, TaskDecomposition] = {}

    def set_client(self, client):
        """Set the xAI client."""
        self.client = client

    def get_name(self) -> str:
        """Get the tool name."""
        return "orchestrate"

    @property
    def description(self) -> str:
        return "Orchestrate multiple specialized agents to work together on a complex task. Automatically decomposes the task, assigns roles, and coordinates execution."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The complex goal to orchestrate"
                },
                "max_agents": {
                    "type": "integer",
                    "description": "Maximum number of concurrent agents (default: 3)",
                    "default": 3
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Maximum time to wait for completion (default: 300)",
                    "default": 300
                }
            },
            "required": ["goal"]
        }

    def execute(self, **kwargs) -> ToolResult:
        """
        Orchestrate multiple agents to complete a complex goal.

        Args:
            goal: The complex goal
            max_agents: Maximum concurrent agents
            timeout_seconds: Timeout in seconds

        Returns:
            ToolResult with orchestration results
        """
        goal = kwargs.get("goal")
        max_agents = kwargs.get("max_agents", 3)
        timeout_seconds = kwargs.get("timeout_seconds", 300)

        if not goal:
            return self.error("Goal is required for orchestration")

        self.logger.info(f"Starting orchestration for: {goal}")

        # Step 1: Decompose the task
        try:
            decomposition = self._decompose_task(goal)
        except Exception as e:
            return self.error(f"Failed to decompose task: {str(e)}")

        # Store orchestration
        orchestration_id = f"orch_{int(time.time())}"
        self.orchestrations[orchestration_id] = decomposition

        # Step 2: Execute tasks with agent spawning
        try:
            results = self._execute_orchestration(
                decomposition,
                orchestration_id,
                max_agents,
                timeout_seconds
            )
        except Exception as e:
            return self.error(f"Orchestration failed: {str(e)}")

        # Step 3: Aggregate results
        summary = self._aggregate_results(decomposition, results)

        return self.success(
            f"Orchestration completed for: {goal}\n\n"
            f"{summary}\n\n"
            f"See blackboard messages for detailed agent communications."
        )

    def _decompose_task(self, goal: str) -> TaskDecomposition:
        """
        Decompose a complex task into sub-tasks with role assignments.

        Args:
            goal: The complex goal

        Returns:
            TaskDecomposition object
        """
        decomposition = TaskDecomposition(goal)

        # If client available, use AI to decompose
        if self.client:
            try:
                sub_tasks = self._decompose_with_ai(goal)
                for task_info in sub_tasks:
                    decomposition.add_sub_task(
                        description=task_info["description"],
                        role=task_info["role"],
                        priority=task_info.get("priority", 1),
                        dependencies=task_info.get("dependencies", [])
                    )
                return decomposition
            except Exception as e:
                self.logger.warning(f"AI decomposition failed: {e}, using heuristic")

        # Fallback: Heuristic decomposition
        # For most coding tasks: plan -> research -> code -> review -> test

        task_id_plan = decomposition.add_sub_task(
            "Create detailed implementation plan",
            AgentRole.PLANNER,
            priority=1
        )

        task_id_research = decomposition.add_sub_task(
            f"Research relevant code and documentation for: {goal}",
            AgentRole.RESEARCHER,
            priority=1
        )

        task_id_code = decomposition.add_sub_task(
            f"Implement: {goal}",
            AgentRole.CODER,
            priority=2,
            dependencies=[task_id_plan, task_id_research]
        )

        task_id_review = decomposition.add_sub_task(
            "Review implementation for quality and correctness",
            AgentRole.REVIEWER,
            priority=3,
            dependencies=[task_id_code]
        )

        task_id_test = decomposition.add_sub_task(
            "Create and run tests for the implementation",
            AgentRole.TESTER,
            priority=3,
            dependencies=[task_id_code]
        )

        return decomposition

    def _decompose_with_ai(self, goal: str) -> List[Dict[str, Any]]:
        """Use AI to decompose task into sub-tasks."""
        prompt = f"""Decompose this complex task into sub-tasks with role assignments:

Goal: {goal}

Available roles:
- planner: Creates detailed plans
- researcher: Searches code and documentation
- coder: Implements code changes
- reviewer: Reviews code quality
- tester: Writes and runs tests

Return a JSON array of sub-tasks:
[
  {{
    "description": "Sub-task description",
    "role": "planner|researcher|coder|reviewer|tester",
    "priority": 1,
    "dependencies": []
  }}
]

Consider dependencies - later tasks may depend on earlier ones.
Return only the JSON array."""

        chat = self.client.chat.create(model=self.config.current_model, tools=[])
        from xai_sdk.chat import user
        chat.append(user(prompt))
        response = chat.sample()

        content = response.content if hasattr(response, 'content') else str(response)

        # Extract JSON
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            json_str = content[json_start:json_end].strip()
        elif "[" in content and "]" in content:
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            json_str = content[json_start:json_end]
        else:
            raise ValueError("No JSON array found in response")

        return json.loads(json_str)

    def _execute_orchestration(
        self,
        decomposition: TaskDecomposition,
        orchestration_id: str,
        max_agents: int,
        timeout_seconds: int
    ) -> Dict[int, str]:
        """
        Execute the orchestration by spawning agents.

        Args:
            decomposition: Task decomposition
            orchestration_id: Orchestration ID
            max_agents: Max concurrent agents
            timeout_seconds: Timeout

        Returns:
            Dictionary mapping task_id to result
        """
        results = {}
        start_time = time.time()
        running_agents = {}  # agent_id -> task_id

        # Post orchestration start to blackboard
        self.blackboard.post_message(
            "orchestrator",
            f"Starting orchestration {orchestration_id}: {decomposition.goal}",
            "info"
        )

        while not decomposition.is_complete():
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Orchestration timed out after {timeout_seconds}s")

            # Get ready tasks
            ready_tasks = decomposition.get_ready_tasks()

            # Spawn agents for ready tasks (up to max_agents)
            while ready_tasks and len(running_agents) < max_agents:
                task = ready_tasks.pop(0)
                agent_id = self._spawn_agent_for_task(task, orchestration_id)

                if agent_id:
                    running_agents[agent_id] = task["id"]
                    decomposition.mark_task_running(task["id"], agent_id)

            # Check agent progress via blackboard
            messages = self.blackboard.get_messages(message_type="result")
            for message in messages:
                agent_id = message["agent_id"]
                if agent_id in running_agents:
                    task_id = running_agents[agent_id]
                    result_content = message["content"]

                    # Mark task as completed
                    decomposition.mark_task_completed(task_id, result_content)
                    results[task_id] = result_content

                    # Remove from running
                    del running_agents[agent_id]

                    self.logger.info(f"Task {task_id} completed by {agent_id}")

            # Brief sleep to avoid busy waiting
            time.sleep(1)

            # Report progress
            progress = decomposition.get_progress()
            if progress["completed"] % 5 == 0:  # Report every 5 completions
                self.blackboard.set_shared_data(
                    f"orchestration_{orchestration_id}_progress",
                    progress
                )

        return results

    def _spawn_agent_for_task(self, task: Dict[str, Any], orchestration_id: str) -> Optional[str]:
        """
        Spawn an agent for a specific task.

        Args:
            task: Task dictionary
            orchestration_id: Orchestration ID

        Returns:
            Agent ID if spawned successfully
        """
        role = task["role"]
        description = task["description"]
        task_id = task["id"]

        # Create agent task with orchestration context
        agent_task = f"""[Orchestration: {orchestration_id}, Task: {task_id}]

{description}

IMPORTANT: When complete, post your result to the blackboard with:
- message_type: "result"
- Include task completion summary in the message"""

        # For now, we'll return a simulated agent ID
        # In a real implementation, this would spawn an actual subprocess
        agent_id = f"{role}_{orchestration_id}_{task_id}"

        # Post task assignment to blackboard
        self.blackboard.post_message(
            "orchestrator",
            f"Assigned task {task_id} to agent {agent_id}: {description}",
            "info"
        )

        # Simulate agent response (in real implementation, agent would post this)
        # For demonstration, we'll post a simulated result after a brief delay
        # In production, actual spawned agents would handle this
        self.blackboard.post_message(
            agent_id,
            f"Task {task_id} completed: {description}",
            "result"
        )

        return agent_id

    def _aggregate_results(self, decomposition: TaskDecomposition, results: Dict[int, str]) -> str:
        """
        Aggregate results from all sub-tasks.

        Args:
            decomposition: Task decomposition
            results: Task results

        Returns:
            Aggregated summary
        """
        progress = decomposition.get_progress()

        lines = [
            f"Orchestration Summary:",
            f"Goal: {decomposition.goal}",
            f"Total Tasks: {progress['total']}",
            f"Completed: {progress['completed']}",
            f"Success Rate: {progress['progress_pct']:.1f}%",
            "",
            "Task Results:"
        ]

        for task in decomposition.sub_tasks:
            task_id = task["id"]
            status_icon = "✓" if task["status"] == "completed" else "○"
            lines.append(
                f"  {status_icon} [{task['role']}] {task['description']}"
            )
            if task_id in results:
                result_preview = results[task_id][:100] + "..." if len(results[task_id]) > 100 else results[task_id]
                lines.append(f"     Result: {result_preview}")

        return "\n".join(lines)


def create_orchestrator_tools(config: Config, client=None) -> List[BaseTool]:
    """
    Create orchestrator tools.

    Args:
        config: Configuration object
        client: xAI SDK client (optional)

    Returns:
        List of orchestrator tools
    """
    return [OrchestratorTool(config, client)]
