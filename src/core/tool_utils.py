import logging

from src.tools import TaskCompletionSignal
from src.ui import display_tool_call, get_console, get_prompt_session

logger = logging.getLogger(__name__)


def handle_tool_calls(response, tool_executor, session, enable_reflection=True):
    """Handle tool calls from the AI response."""
    console = get_console()
    tool_results = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            # Display tool call
            display_tool_call(tool_call.function.name, {})

            try:
                # Execute tool call - returns ToolResult with structured success/failure
                tool_result = tool_executor.execute_tool_call(
                    {
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                    }
                )

                tool_success = tool_result.success
                result_text = tool_result.result

            except TaskCompletionSignal as signal:
                # Task completion signal caught - add tool result first
                session.add_message(
                    "tool",
                    f"Task completed: {signal.summary}",
                    tool_name="task_completed"
                )
                tool_results.append(("task_completed", f"Task completed: {signal.summary}"))

                # Then trigger user interaction
                handle_task_completion_interaction(
                    session,
                    signal.summary,
                    signal.next_steps
                )

                # Continue processing remaining tools if any
                continue

            # Add tool result to session with proper tool name
            session.add_message("tool", result_text, tool_name=tool_call.function.name)
            tool_results.append((tool_call.function.name, result_text))

            # Display tool success/failure (brief)
            if tool_success:
                console.print(f"[dim]✓ {tool_call.function.name} completed[/dim]")
            else:
                console.print(f"[yellow]⚠ {tool_call.function.name} completed with warnings/errors[/yellow]")

                # Add reflection on failure if enabled
                if enable_reflection and hasattr(session, 'episodic_memory') and session.episodic_memory.current_episode:
                    session.episodic_memory.add_action_to_current_episode(
                        action_type="tool_call",
                        description=f"{tool_call.function.name}: {tool_call.function.arguments[:100]}...",
                        result=result_text[:200],
                        success=False
                    )

    return tool_results

def handle_task_completion_interaction(session, summary: str, next_steps: str = "") -> bool:
    """
    Handle task completion interaction with user.
    """
    console = get_console()
    prompt_session = get_prompt_session()

    # Check if context usage exceeds threshold (user requirement: 128k)
    context_stats = session.get_context_info()
    estimated_tokens = context_stats.get('estimated_tokens', 0)
    threshold = session.config.task_completion_token_threshold

    if estimated_tokens < threshold:
        # Below threshold - just acknowledge completion
        console.print(f"\n[green]✓ Task completed:[/green] {summary}")
        if next_steps:
            console.print(f"[dim]Suggested next steps: {next_steps}[/dim]\n")
        return False

    # Above threshold - offer context management
    console.print("\n[bold green]✓ Task Completed[/bold green]")
    console.print(f"[dim]{summary}[/dim]")
    if next_steps:
        console.print(f"[dim]Next steps: {next_steps}[/dim]")

    console.print(f"\n[yellow]Context usage: {estimated_tokens:,} tokens (threshold: {threshold:,})[/yellow]")
    console.print("Would you like to clear context to free up memory? (Y/n): ", end="")

    try:
        choice = prompt_session.prompt("").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Keeping context.[/dim]")
        return False

    if choice in ['y', 'yes', '']:  # Default to yes per user requirement
        # Clear context but keep system prompt and memories
        session.clear_context(keep_system_prompt=True)
        console.print("[green]✓ Context cleared. Memories and system prompt preserved.[/green]\n")
        return True
    else:
        console.print("[dim]Context preserved.[/dim]\n")
        return False
