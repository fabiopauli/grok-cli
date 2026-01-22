#!/usr/bin/env python3

"""
Agentic reasoning commands for Grok Assistant

Commands for planning, reflection, self-improvement, and multi-agent coordination.
"""

from .base import BaseCommand, CommandResult
from ..ui.console import get_console


class PlanCommand(BaseCommand):
    """Command to trigger explicit planning for a task."""

    @property
    def name(self) -> str:
        return "/plan"

    @property
    def description(self) -> str:
        return "Create a structured plan for a complex task using ReAct-style planning"

    @property
    def usage(self) -> str:
        return "/plan <goal> - Generate a step-by-step plan for achieving a goal"

    def execute(self, session, args: str = "") -> CommandResult:
        """Execute plan command."""
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

            # Display response
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=session.config.enable_markdown_rendering,
                    code_theme=session.config.markdown_code_theme
                )

            # Handle any tool calls (planning)
            if hasattr(response, "tool_calls") and response.tool_calls:
                from ..main import handle_tool_calls
                from ..core.app_context import AppContext
                # Get tool executor from global context (or we could pass it)
                # For now, just inform user
                console.print("[yellow]Planning tool would be invoked here. Use the generate_plan tool directly for now.[/yellow]")

            session.complete_turn("Planning completed")

        except Exception as e:
            console.print(f"[red]Error during planning: {e}[/red]")
            session.complete_turn(f"Planning failed: {str(e)}")

        return CommandResult(should_continue=True)


class ImproveCommand(BaseCommand):
    """Command to trigger self-improvement loops."""

    @property
    def name(self) -> str:
        return "/improve"

    @property
    def description(self) -> str:
        return "Trigger self-improvement by analyzing past episodes and generating optimizations"

    @property
    def usage(self) -> str:
        return "/improve - Analyze recent episodes and suggest improvements"

    def execute(self, session, args: str = "") -> CommandResult:
        """Execute improve command."""
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

    @property
    def name(self) -> str:
        return "/spawn"

    @property
    def description(self) -> str:
        return "Spawn a specialized agent (planner, coder, reviewer, researcher, tester)"

    @property
    def usage(self) -> str:
        return "/spawn <role> <task> - Spawn an agent with a specific role and task"

    def execute(self, session, args: str = "") -> CommandResult:
        """Execute spawn command."""
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

        console.print(f"[cyan]🤖 Spawning {role} agent...[/cyan]")

        # Add spawn request to session
        spawn_message = f"Please use the spawn_agent tool to create a {role} agent for this task: {task}"
        session.add_message("user", spawn_message)

        try:
            # Get AI response (should trigger spawn tool)
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

            session.complete_turn("Agent spawn completed")

        except Exception as e:
            console.print(f"[red]Error spawning agent: {e}[/red]")
            session.complete_turn(f"Agent spawn failed: {str(e)}")

        return CommandResult(should_continue=True)


class EpisodesCommand(BaseCommand):
    """Command to view episodic memory."""

    @property
    def name(self) -> str:
        return "/episodes"

    @property
    def description(self) -> str:
        return "View recent episodes from episodic memory"

    @property
    def usage(self) -> str:
        return "/episodes [limit] - Show recent episodes (default: 10)"

    def execute(self, session, args: str = "") -> CommandResult:
        """Execute episodes command."""
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
        EpisodesCommand(config)
    ]
