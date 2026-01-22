import json
from typing import List

from src.ui import get_console, get_prompt_session, display_tool_call
from src.tools import TaskCompletionSignal

def handle_tool_calls(response, tool_executor, session, enable_reflection=True):
    """Handle tool calls from the AI response."""
    console = get_console()
    tool_results = []

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            # Display tool call
            display_tool_call(tool_call.function.name, {})

            tool_success = True
            try:
                # Execute tool call
                result = tool_executor.execute_tool_call(
                    {
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        }
                    }
                )

                # Check if result indicates failure
                if isinstance(result, str) and (result.startswith("Error") or "failed" in result.lower()):
                    tool_success = False

            except TaskCompletionSignal as signal:
                # Task completion signal caught - add tool result first
                session.add_message(
                    "tool",
                    f"Task completed: {signal.summary}",
                    tool_name="task_completed"
                )
                tool_results.append(("task_completed", f"Task completed: {signal.summary}"))

                # Then trigger user interaction
                context_cleared = handle_task_completion_interaction(
                    session,
                    signal.summary,
                    signal.next_steps
                )

                # Continue processing remaining tools if any
                continue

            # Auto-mount files when read by AI
            if tool_call.function.name == "read_file":
                # Parse arguments to get file path
                try:
                    args = json.loads(tool_call.function.arguments)
                    file_path = args.get("file_path")
                    if file_path and not result.startswith("Error"):
                        # Track file in context to prevent duplicate reads
                        if hasattr(session.context_manager, 'add_file_to_context'):
                            session.context_manager.add_file_to_context(file_path)

                        # Extract content from result (format: "Content of file '...':\n\n&lt;content&gt;")
                        content_marker = "\n\n"
                        if content_marker in result:
                            content = result.split(content_marker, 1)[1]
                            # Mount the file to context
                            session.mount_file(file_path, content)
                            console.print(f"[dim]→ Mounted '{file_path}' to context[/dim]")
                except (json.JSONDecodeError, Exception):
                    pass  # If we can't mount, just continue

            elif tool_call.function.name == "read_multiple_files":
                # Parse result to get successfully read files
                try:
                    result_data = json.loads(result)
                    files_read = result_data.get("files_read", {})
                    for file_path, content in files_read.items():
                        # Track file in context to prevent duplicate reads
                        if hasattr(session.context_manager, 'add_file_to_context'):
                            session.context_manager.add_file_to_context(file_path)
                        session.mount_file(file_path, content)
                    if files_read:
                        console.print(f"[dim]→ Mounted {len(files_read)} files to context[/dim]")
                except (json.JSONDecodeError, Exception):
                    pass  # If we can't mount, just continue

            # Add tool result to session with proper tool name
            session.add_message("tool", result, tool_name=tool_call.function.name)
            tool_results.append((tool_call.function.name, result))

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
                        result=result[:200],
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
    console.print(f"\n[bold green]✓ Task Completed[/bold green]")
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
