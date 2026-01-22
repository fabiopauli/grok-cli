#!/usr/bin/env python3

"""
Planning and Reflection Tools for Agentic Reasoning

Implements ReAct-style planning and critique loops for improved
multi-step task handling and self-correction.
"""

import json
from typing import Any

from .base import BaseTool, ToolResult
from ..core.config import Config
from ..utils.logging_config import get_logger


class GeneratePlanTool(BaseTool):
    """
    Tool for generating structured plans for complex tasks.

    Implements ReAct-style planning by breaking down complex tasks
    into step-by-step action sequences.
    """

    def __init__(self, config: Config, client=None):
        """
        Initialize the planning tool.

        Args:
            config: Configuration object
            client: xAI SDK client for internal reasoning calls
        """
        super().__init__(config)
        self.client = client
        self.logger = get_logger("planning")

    def set_client(self, client):
        """Set the xAI client for internal calls."""
        self.client = client

    def get_name(self) -> str:
        """Get the tool name."""
        return "generate_plan"

    @property
    def description(self) -> str:
        return "Generate a structured step-by-step plan for completing complex tasks. Use this for multi-file refactors, debugging workflows, or tasks requiring multiple coordinated actions."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The high-level goal or task to plan for"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the current state, constraints, or requirements"
                },
                "max_steps": {
                    "type": "integer",
                    "description": "Maximum number of steps in the plan",
                    "default": 10
                }
            },
            "required": ["goal"]
        }

    def execute(self, **kwargs) -> ToolResult:
        """
        Generate a structured plan for the given goal.

        Args:
            goal: The task or goal to plan for
            context: Additional context (optional)
            max_steps: Maximum number of steps (default: 10)

        Returns:
            ToolResult with the generated plan
        """
        goal = kwargs.get("goal")
        context = kwargs.get("context", "")
        max_steps = kwargs.get("max_steps", 10)

        if not goal:
            return ToolResult.fail("Goal is required for planning")

        # Create planning prompt
        planning_prompt = self._create_planning_prompt(goal, context, max_steps)

        # If client is available, use it to generate plan internally
        if self.client:
            try:
                plan = self._generate_plan_with_model(planning_prompt)
            except Exception as e:
                self.logger.error(f"Error generating plan with model: {e}")
                plan = self._generate_simple_plan(goal, max_steps)
        else:
            # Fallback: create a simple template plan
            plan = self._generate_simple_plan(goal, max_steps)

        # Store plan in config for main loop to use
        if hasattr(self.config, '_current_plan'):
            self.config._current_plan = plan

        # Format plan for output
        plan_text = self._format_plan(plan)

        return ToolResult.ok(
            f"Generated plan for: {goal}\n\n{plan_text}\n\n"
            "The plan has been stored and will guide subsequent actions."
        )

    def _create_planning_prompt(self, goal: str, context: str, max_steps: int) -> str:
        """Create the planning prompt."""
        prompt = f"""Generate a detailed step-by-step plan for the following task:

Goal: {goal}
"""
        if context:
            prompt += f"\nContext: {context}"

        prompt += f"""

Create a plan with up to {max_steps} steps. Each step should:
1. Be specific and actionable
2. Include the tool or action needed
3. Specify expected outcome/observation
4. Build upon previous steps

Format as JSON:
{{
    "goal": "{goal}",
    "steps": [
        {{
            "step_number": 1,
            "action": "Tool or action to perform",
            "description": "Detailed description",
            "expected_outcome": "What should result",
            "dependencies": []
        }}
    ]
}}

Return only the JSON plan."""
        return prompt

    def _generate_plan_with_model(self, prompt: str) -> dict:
        """Generate plan using the AI model."""
        # Create a simple chat for planning
        chat = self.client.chat.create(
            model=self.config.current_model,
            tools=[]  # No tools for planning
        )

        from xai_sdk.chat import user
        chat.append(user(prompt))
        response = chat.sample()

        # Extract and parse JSON plan
        content = response.content if hasattr(response, 'content') else str(response)

        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            plan = json.loads(json_str)
            return plan
        except Exception as e:
            self.logger.warning(f"Failed to parse plan JSON: {e}")
            return {"goal": prompt[:100], "steps": []}

    def _generate_simple_plan(self, goal: str, max_steps: int) -> dict:
        """Generate a simple template plan as fallback."""
        return {
            "goal": goal,
            "steps": [
                {
                    "step_number": 1,
                    "action": "Analyze current state",
                    "description": "Understand the current codebase and identify what needs to change",
                    "expected_outcome": "Clear understanding of requirements",
                    "dependencies": []
                },
                {
                    "step_number": 2,
                    "action": "Execute main task",
                    "description": f"Complete the goal: {goal}",
                    "expected_outcome": "Task completed successfully",
                    "dependencies": [1]
                },
                {
                    "step_number": 3,
                    "action": "Verify and test",
                    "description": "Verify changes work correctly",
                    "expected_outcome": "All tests pass, goal achieved",
                    "dependencies": [2]
                }
            ]
        }

    def _format_plan(self, plan: dict) -> str:
        """Format plan as readable text."""
        lines = [f"Goal: {plan.get('goal', 'Unknown')}"]
        lines.append("\nSteps:")

        for step in plan.get("steps", []):
            step_num = step.get("step_number", "?")
            action = step.get("action", "")
            description = step.get("description", "")
            expected = step.get("expected_outcome", "")

            lines.append(f"\n{step_num}. {action}")
            lines.append(f"   Description: {description}")
            lines.append(f"   Expected: {expected}")

        return "\n".join(lines)


class ReflectTool(BaseTool):
    """
    Tool for reflecting on and critiquing tool execution outcomes.

    Implements Reflexion-style critique loops for self-correction
    and iterative improvement.
    """

    def __init__(self, config: Config, client=None):
        """
        Initialize the reflection tool.

        Args:
            config: Configuration object
            client: xAI SDK client for internal reasoning calls
        """
        super().__init__(config)
        self.client = client
        self.logger = get_logger("reflection")

    def set_client(self, client):
        """Set the xAI client for internal calls."""
        self.client = client

    def get_name(self) -> str:
        """Get the tool name."""
        return "reflect"

    @property
    def description(self) -> str:
        return "Reflect on and critique the outcome of previous actions. Use this after failed tool executions or unexpected results to generate improved approaches."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action or tool that was executed"
                },
                "outcome": {
                    "type": "string",
                    "description": "The actual outcome or result"
                },
                "expected": {
                    "type": "string",
                    "description": "What was expected to happen"
                },
                "error": {
                    "type": "string",
                    "description": "Error message if the action failed"
                }
            },
            "required": ["action", "outcome"]
        }

    def execute(self, **kwargs) -> ToolResult:
        """
        Reflect on an action's outcome and generate critique.

        Args:
            action: The action that was executed
            outcome: The actual outcome
            expected: What was expected (optional)
            error: Error message if failed (optional)

        Returns:
            ToolResult with reflection and suggested improvements
        """
        action = kwargs.get("action")
        outcome = kwargs.get("outcome")
        expected = kwargs.get("expected", "")
        error = kwargs.get("error", "")

        if not action or not outcome:
            return ToolResult.fail("Both 'action' and 'outcome' are required for reflection")

        # Create reflection prompt
        reflection_prompt = self._create_reflection_prompt(action, outcome, expected, error)

        # Generate reflection
        if self.client:
            try:
                reflection = self._generate_reflection_with_model(reflection_prompt)
            except Exception as e:
                self.logger.error(f"Error generating reflection: {e}")
                reflection = self._generate_simple_reflection(action, outcome, error)
        else:
            reflection = self._generate_simple_reflection(action, outcome, error)

        # Store reflection in memory
        self._store_reflection(action, outcome, reflection)

        return ToolResult.ok(
            f"Reflection on '{action}':\n\n{reflection}\n\n"
            "This reflection has been stored in memory for future reference."
        )

    def _create_reflection_prompt(self, action: str, outcome: str, expected: str, error: str) -> str:
        """Create the reflection prompt."""
        prompt = f"""Reflect on the following action and its outcome:

Action: {action}
Outcome: {outcome}
"""
        if expected:
            prompt += f"Expected: {expected}\n"
        if error:
            prompt += f"Error: {error}\n"

        prompt += """
Provide a critical analysis:
1. What went wrong (if anything)?
2. Why did it happen?
3. What should be done differently next time?
4. Revised approach or plan

Be concise and actionable."""
        return prompt

    def _generate_reflection_with_model(self, prompt: str) -> str:
        """Generate reflection using the AI model."""
        chat = self.client.chat.create(
            model=self.config.current_model,
            tools=[]
        )

        from xai_sdk.chat import user
        chat.append(user(prompt))
        response = chat.sample()

        return response.content if hasattr(response, 'content') else str(response)

    def _generate_simple_reflection(self, action: str, outcome: str, error: str) -> str:
        """Generate a simple reflection as fallback."""
        if error:
            return f"""Analysis: The action '{action}' failed with error: {error}

Suggested approach:
1. Review the error message carefully
2. Check input parameters and preconditions
3. Consider alternative approaches
4. Verify environment and dependencies
5. Try again with corrected parameters"""
        else:
            return f"""Analysis: The action '{action}' completed with outcome: {outcome}

Consider:
1. Was this the expected result?
2. Are there any side effects to check?
3. Should we verify the outcome?
4. What are the next steps?"""

    def _store_reflection(self, action: str, outcome: str, reflection: str) -> None:
        """Store reflection in memory for future reference."""
        # Store as a memory if memory manager is available
        if hasattr(self.config, '_memory_manager'):
            memory_manager = self.config._memory_manager
            memory_manager.save_memory(
                content=f"Reflection on '{action}': {reflection[:200]}...",
                memory_type="reflection",
                scope="directory"
            )


def create_planning_tools(config: Config, client=None) -> list[BaseTool]:
    """
    Create planning and reflection tools.

    Args:
        config: Configuration object
        client: xAI SDK client (optional)

    Returns:
        List of planning tools
    """
    plan_tool = GeneratePlanTool(config, client)
    reflect_tool = ReflectTool(config, client)

    return [plan_tool, reflect_tool]
