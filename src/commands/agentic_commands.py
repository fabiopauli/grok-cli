#!/usr/bin/env python3

"""
Agentic reasoning commands for Grok Assistant

Commands for planning, reflection, self-improvement, and multi-agent coordination.
"""

import time

from .base import BaseCommand, CommandResult
from ..core.tool_utils import handle_tool_calls
from ..ui.console import get_console
from ..utils.async_utils import InterruptiblePoller


class PlanCommand(BaseCommand):
    """Command to trigger explicit planning for a task."""

    def get_pattern(self) -> str:
        return "/plan"

    def get_description(self) -> str:
        return "Create a structured plan for a complex task using ReAct-style planning"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute plan command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        if not args.strip():
            console.print("[yellow]Usage: /plan <goal>[/yellow]")
            console.print("[dim]Example: /plan Refactor the authentication system to use OAuth2[/dim]")
            return CommandResult(should_continue=True)

        goal = args.strip()

        # Start an episode for this planning task
        episode_id = session.episodic_memory.start_episode(goal, scope="directory")
        console.print(f"[dim]Started episode {episode_id} for planning[/dim]")

        # Add planning request to session
        planning_message = f"Please use the generate_plan tool to create a detailed plan for: {goal}"
        session.add_message("user", planning_message)

        try:
            # Get AI response (should trigger planning tool)
            from ..ui.console import display_thinking_indicator, display_assistant_response
            display_thinking_indicator()
            response = session.get_response()

            # Display initial response content if any
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=session.config.enable_markdown_rendering,
                    code_theme=session.config.markdown_code_theme
                )

            # Handle tool calls
            if hasattr(response, "tool_calls") and response.tool_calls:
                handle_tool_calls(response, session.tool_executor, session)
                console.print("[green]✓ Planning tools executed[/green]")

                # Get final response after tools
                display_thinking_indicator()
                response = session.get_response()

            # Display final response
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=session.config.enable_markdown_rendering,
                    code_theme=session.config.markdown_code_theme
                )

            session.complete_turn("Planning completed")

        except Exception as e:
            console.print(f"[red]Error during planning: {e}[/red]")
            session.complete_turn(f"Planning failed: {str(e)}")

        return CommandResult(should_continue=True)


class ImproveCommand(BaseCommand):
    """Command to trigger self-improvement loops."""

    def get_pattern(self) -> str:
        return "/improve"

    def get_description(self) -> str:
        return "Trigger self-improvement by analyzing past episodes and generating optimizations"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute improve command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        console.print("[cyan]🔍 Analyzing recent episodes for improvement opportunities...[/cyan]")

        # Get episode statistics
        stats = session.episodic_memory.get_statistics()

        console.print(f"\n[bold]Episode Statistics:[/bold]")
        console.print(f"  Total episodes: {stats['total_episodes']}")
        console.print(f"  Completed: {stats['completed_episodes']}")
        console.print(f"  Successful: {stats['successful_episodes']}")
        console.print(f"  Success rate: {stats['success_rate']:.1%}")

        # Get failed episodes for analysis
        all_episodes = session.episodic_memory.get_episodes(limit=20)
        failed_episodes = [ep for ep in all_episodes if ep.completed and not ep.success]

        if not failed_episodes:
            console.print("\n[green]✓ No failed episodes found. System performing well![/green]")
            return CommandResult(should_continue=True)

        console.print(f"\n[yellow]Found {len(failed_episodes)} failed episodes to analyze[/yellow]")

        # Analyze failures
        failure_patterns = {}
        for episode in failed_episodes[:5]:  # Analyze top 5 failures
            console.print(f"\n[dim]Episode: {episode.goal}[/dim]")
            console.print(f"[dim]Outcome: {episode.outcome}[/dim]")

            # Count action types that failed
            for action in episode.actions:
                if not action.get("success", True):
                    action_type = action.get("type", "unknown")
                    failure_patterns[action_type] = failure_patterns.get(action_type, 0) + 1

        # Generate improvement suggestions
        console.print("\n[bold cyan]Improvement Suggestions:[/bold cyan]")

        if failure_patterns:
            console.print("\n[yellow]Most common failure types:[/yellow]")
            sorted_patterns = sorted(failure_patterns.items(), key=lambda x: x[1], reverse=True)
            for action_type, count in sorted_patterns[:3]:
                console.print(f"  • {action_type}: {count} failures")

        # Suggest creating tools for common patterns
        suggestions = [
            "Consider creating specialized tools for frequently failing operations",
            "Review error handling in tools that fail often",
            "Add validation checks before executing risky operations",
            "Create helper functions for common task patterns"
        ]

        console.print("\n[bold]Actionable improvements:[/bold]")
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"{i}. {suggestion}")

        # Offer to create improvement tasks
        if session.config.agent_mode:
            console.print("\n[cyan]Agent mode enabled - would auto-generate improvement tasks[/cyan]")
            # In agent mode, could automatically create tasks or tools

        return CommandResult(should_continue=True)


class SpawnCommand(BaseCommand):
    """Command to spawn specialized agents."""

    def get_pattern(self) -> str:
        return "/spawn"

    def get_description(self) -> str:
        return "Spawn a specialized agent (planner, coder, reviewer, researcher, tester)"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute spawn command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        if not args.strip():
            console.print("[yellow]Usage: /spawn <role> <task>[/yellow]")
            console.print("[dim]Available roles: planner, coder, reviewer, researcher, tester[/dim]")
            console.print("[dim]Example: /spawn reviewer Review the authentication module for security issues[/dim]")
            return CommandResult(should_continue=True)

        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            console.print("[yellow]Both role and task are required[/yellow]")
            return CommandResult(should_continue=True)

        role, task = parts

        valid_roles = ["planner", "coder", "reviewer", "researcher", "tester"]
        if role not in valid_roles:
            console.print(f"[yellow]Invalid role: {role}[/yellow]")
            console.print(f"[dim]Valid roles: {', '.join(valid_roles)}[/dim]")
            return CommandResult(should_continue=True)

        console.print(f"[cyan]🤖 Spawning {role} agent for task: {task}[/cyan]")

        # Start an episode for this spawn task
        episode_id = session.episodic_memory.start_episode(f"Spawn {role} agent for: {task}", scope="directory")
        console.print(f"[dim]Started episode {episode_id} for agent spawn[/dim]")

        # Add spawn request to session - MUST use spawn_agent tool
        spawn_message = (
            f"CRITICAL: You MUST call the spawn_agent tool NOW. Do NOT execute the task yourself.\n\n"
            f"Call spawn_agent with these exact parameters:\n"
            f"- role: \"{role}\"\n"
            f"- task: \"{task}\"\n"
            f"- background: true\n\n"
            f"Do NOT provide the task results directly. Do NOT use read_file, write_file, or any other tools.\n"
            f"ONLY call spawn_agent and nothing else."
        )
        session.add_message("user", spawn_message)

        try:
            # Get AI response for validation/enhancement
            from ..ui.console import display_thinking_indicator, display_assistant_response
            display_thinking_indicator()
            response = session.get_response()

            # Display initial response content if any
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=session.config.enable_markdown_rendering,
                    code_theme=session.config.markdown_code_theme
                )

            # Handle tool calls
            agent_id = None
            used_spawn_tool = False
            tools_used = []

            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_results = handle_tool_calls(response, session.tool_executor, session)
                console.print("[green]✓ Tools executed[/green]")

                # Extract agent_id from tool results
                for tool_name, result in tool_results:
                    tools_used.append(tool_name)

                    if tool_name == "spawn_agent":
                        used_spawn_tool = True
                        if "SPAWN_AGENT_ID:" in result:
                            import re
                            match = re.search(r'SPAWN_AGENT_ID: (\w+)', result)
                            if match:
                                agent_id = match.group(1)
                                break
                        else:
                            # Tool was called but failed
                            console.print(f"[yellow]⚠ spawn_agent tool failed: {result[:200]}[/yellow]")
                    elif tool_name in ["create_file", "write_file", "read_file", "execute_command"]:
                        # AI executed the task directly instead of spawning an agent
                        console.print("[yellow]⚠ The AI executed the task directly instead of spawning an agent.[/yellow]")
                        console.print("[yellow]Task completed without delegation.[/yellow]")
                        session.complete_turn("Task completed directly without spawning agent")
                        return CommandResult(should_continue=True)

            if not used_spawn_tool:
                console.print("[red]Error: AI did not use the spawn_agent tool as instructed.[/red]")
                if tools_used:
                    console.print(f"[yellow]Tools used instead: {', '.join(tools_used)}[/yellow]")
                else:
                    console.print("[yellow]AI responded with text instead of calling a tool.[/yellow]")
                console.print("[yellow]Please try again or execute the task directly.[/yellow]")
                session.complete_turn("Agent spawn failed: spawn_agent tool not used")
                return CommandResult(should_continue=True)

            if not agent_id:
                console.print("[red]Failed to extract agent ID from spawn result[/red]")
                session.complete_turn("Agent spawn failed: no agent ID")
                return CommandResult(should_continue=True)

            console.print(f"[dim]Agent {agent_id} spawned in background. Waiting for results...[/dim]")
            console.print(f"[dim]Press Ctrl+C to cancel waiting[/dim]")

            # Wait for agent to complete and post results on blackboard
            from ..tools.multiagent_tool import BlackboardCommunication
            blackboard_path = session.config.base_dir / ".grok_blackboard.json"
            blackboard = BlackboardCommunication(blackboard_path)

            # Poll for results using interruptible poller (up to 60 seconds)
            # Uses 2s poll intervals with 0.1s interrupt checks for responsive cancellation
            agent_results = []
            was_cancelled = False

            try:
                with InterruptiblePoller(timeout=60, poll_interval=2.0, check_interval=0.1) as poller:
                    while not poller.should_stop():
                        messages = blackboard.get_messages(since=0, message_type="result")
                        # Filter messages from this agent
                        for msg in messages:
                            if msg["agent_id"] == agent_id and "result" in msg["content"].lower():
                                agent_results.append(msg["content"])

                        if agent_results:
                            break

                        poller.wait()

            except KeyboardInterrupt:
                was_cancelled = True
                console.print("\n[yellow]Cancelled waiting for agent results[/yellow]")

            if was_cancelled:
                session.complete_turn("Agent spawn cancelled by user")
                return CommandResult(should_continue=True)

            if not agent_results:
                console.print("[yellow]Timeout waiting for agent results. Checking final blackboard state...[/yellow]")
                # Get latest messages anyway
                messages = blackboard.get_messages(since=0, message_type="result")
                agent_results = [msg["content"] for msg in messages if msg["agent_id"] == agent_id]

            # Send results back to LLM for final processing
            if agent_results:
                results_text = "\n".join(agent_results)
                final_message = f"The {role} agent completed its task. Here are the results:\n\n{results_text}\n\nPlease provide a final summary and any additional insights."
                session.add_message("user", final_message)

                # Get final AI response
                display_thinking_indicator()
                final_response = session.get_response()

                if hasattr(final_response, "content") and final_response.content:
                    display_assistant_response(
                        final_response.content,
                        enable_markdown=session.config.enable_markdown_rendering,
                        code_theme=session.config.markdown_code_theme
                    )
                else:
                    console.print("[dim]No final response from LLM[/dim]")
            else:
                console.print("[red]No results received from agent[/red]")

            session.complete_turn("Agent spawn and processing completed")

        except Exception as e:
            console.print(f"[red]Error spawning agent: {e}[/red]")
            session.complete_turn(f"Agent spawn failed: {str(e)}")

        return CommandResult(should_continue=True)


class EpisodesCommand(BaseCommand):
    """Command to view episodic memory."""

    def get_pattern(self) -> str:
        return "/episodes"

    def get_description(self) -> str:
        return "View recent episodes from episodic memory"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute episodes command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        # Parse limit
        try:
            limit = int(args.strip()) if args.strip() else 10
        except ValueError:
            limit = 10

        episodes = session.episodic_memory.get_episodes(limit=limit)

        if not episodes:
            console.print("[dim]No episodes found.[/dim]")
            return CommandResult(should_continue=True)

        console.print(f"\n[bold cyan]Recent Episodes (showing {len(episodes)}):[/bold cyan]\n")

        for episode in episodes:
            # Status icon
            if episode.success:
                status_icon = "[green]✓[/green]"
            elif episode.success is False:
                status_icon = "[red]✗[/red]"
            else:
                status_icon = "[yellow]⧗[/yellow]"

            # Format episode
            console.print(f"{status_icon} [bold]{episode.goal}[/bold]")
            console.print(f"   ID: {episode.episode_id}")
            console.print(f"   Created: {episode.created}")

            if episode.completed:
                console.print(f"   Completed: {episode.completed}")

            if episode.outcome:
                console.print(f"   Outcome: {episode.outcome}")

            console.print(f"   Actions: {len(episode.actions)}, Reflections: {len(episode.reflections)}")
            console.print()

        # Show statistics
        stats = session.episodic_memory.get_statistics()
        console.print(f"[dim]Total episodes: {stats['total_episodes']} | Success rate: {stats['success_rate']:.1%}[/dim]")

        return CommandResult(should_continue=True)


class BlackboardCommand(BaseCommand):
    """Command to read messages from the shared agent blackboard."""

    def get_pattern(self) -> str:
        return "/blackboard"

    def get_description(self) -> str:
        return "Read messages from the shared agent blackboard"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute blackboard command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        # Parse arguments
        message_type = None
        new_only = True

        if args.strip():
            parts = args.strip().split()
            if parts:
                if parts[0] in ["info", "request", "result", "error"]:
                    message_type = parts[0]
                    if len(parts) > 1 and parts[1].lower() == "all":
                        new_only = False
                elif parts[0].lower() == "all":
                    new_only = False

        # Use the read_blackboard tool logic directly
        from ..tools.multiagent_tool import BlackboardCommunication
        blackboard_path = session.config.base_dir / ".grok_blackboard.json"
        blackboard = BlackboardCommunication(blackboard_path)

        # Get last read time from session or tool instance
        last_read_time = getattr(session, '_blackboard_last_read', 0)

        since = last_read_time if new_only else None
        messages = blackboard.get_messages(since=since, message_type=message_type)

        # Update last read time
        session._blackboard_last_read = time.time()

        if not messages:
            console.print("[dim]No messages on the blackboard.[/dim]")
            return CommandResult(should_continue=True)

        console.print(f"\n[bold cyan]Blackboard Messages ({len(messages)} total):[/bold cyan]\n")

        for msg in messages:
            timestamp = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
            agent_id = msg["agent_id"]
            msg_type = msg["type"]
            content = msg["content"]

            # Color code by type
            type_color = {
                "info": "blue",
                "request": "yellow",
                "result": "green",
                "error": "red"
            }.get(msg_type, "white")

            console.print(f"[{type_color}]{timestamp}[/{type_color}] [bold]{agent_id}[/bold] ({msg_type}): {content}")

        return CommandResult(should_continue=True)


class OrchestrateCommand(BaseCommand):
    """Command to orchestrate multiple agents on a complex task."""

    def get_pattern(self) -> str:
        return "/orchestrate"

    def get_description(self) -> str:
        return "Orchestrate multiple specialized agents to work together on a complex task"

    def execute(self, user_input: str, session) -> CommandResult:
        """Execute orchestrate command."""
        args = self.extract_arguments(user_input)
        console = get_console()

        if not args.strip():
            console.print("[yellow]Usage: /orchestrate <complex goal>[/yellow]")
            console.print("[dim]Example: /orchestrate Implement a complete authentication system with OAuth2, 2FA, and session management[/dim]")
            return CommandResult(should_continue=True)

        goal = args.strip()

        console.print(f"[cyan]🎭 Orchestrating agents for complex task...[/cyan]")
        console.print(f"[dim]Goal: {goal}[/dim]\n")

        # Start an episode for this orchestration
        episode_id = session.episodic_memory.start_episode(goal, scope="directory")
        console.print(f"[dim]Started episode {episode_id} for orchestration[/dim]")

        # Add orchestration request to session
        orchestrate_message = f"Please use the orchestrate tool to coordinate multiple agents for this complex task: {goal}"
        session.add_message("user", orchestrate_message)

        try:
            # Get AI response (should trigger orchestrate tool)
            from ..ui.console import display_thinking_indicator, display_assistant_response
            display_thinking_indicator()
            response = session.get_response()

            # Display response
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=session.config.enable_markdown_rendering,
                    code_theme=session.config.markdown_code_theme
                )

            session.complete_turn("Orchestration completed")

        except Exception as e:
            console.print(f"[red]Error during orchestration: {e}[/red]")
            session.complete_turn(f"Orchestration failed: {str(e)}")

        return CommandResult(should_continue=True)


def create_agentic_commands(config) -> list[BaseCommand]:
    """
    Create agentic reasoning commands.

    Args:
        config: Configuration object

    Returns:
        List of agentic commands
    """
    return [
        PlanCommand(config),
        ImproveCommand(config),
        SpawnCommand(config),
        BlackboardCommand(config),
        EpisodesCommand(config),
        OrchestrateCommand(config)
    ]
