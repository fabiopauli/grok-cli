#!/usr/bin/env python3

"""
Main application for Grok Assistant (Refactored)

This is the new, thin orchestrator that coordinates all the modular components.

Supports two modes:
- Interactive mode: grok-cli (starts REPL)
- One-shot mode: grok-cli "your prompt here"
"""

import argparse
import contextlib
import json
import sys

from dotenv import load_dotenv

from src.commands import create_command_registry
from src.core.app_context import AppContext
from src.core.config import Config
from src.core.session import GrokSession
from src.core.tool_utils import handle_task_completion_interaction
from src.tools import TaskCompletionSignal, create_tool_executor
from src.ui import (
    display_assistant_response,
    display_error,
    display_startup_banner,
    display_thinking_indicator,
    display_tool_call,
    get_console,
    get_prompt_indicator,
    get_prompt_session,
    initialize_prompt_session,
)
from src.utils.logging_config import get_logger, setup_logging
from src.utils.shell_utils import detect_available_shells


def initialize_application() -> AppContext:
    """
    Initialize the application with all required components.

    Returns:
        AppContext with all dependencies configured
    """
    # Setup logging first
    setup_logging()
    logger = get_logger("main")
    logger.info("Grok Assistant initializing...")

    # Load environment variables
    load_dotenv()

    # Initialize configuration
    config = Config()
    logger.info(f"Configuration loaded: model={config.current_model}, base_dir={config.base_dir}")

    # Detect available shells
    detect_available_shells(config)

    # Initialize UI components
    initialize_prompt_session()

    # Create AppContext with production dependencies
    context = AppContext.create_production(config=config)

    # Create command registry
    command_registry = create_command_registry(config)
    context.set_command_registry(command_registry)

    # Create tool executor (pass client for planning tools)
    tool_executor = create_tool_executor(config, client=context.client)
    context.set_tool_executor(tool_executor)

    return context


def handle_tool_calls(response, tool_executor, session, enable_reflection=True):
    """
    Handle tool calls from the AI response.

    Args:
        response: Response from AI
        tool_executor: Tool executor instance
        session: Current session
        enable_reflection: Enable reflection on failures (default: True)

    Returns:
        List of tool results
    """
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
                tool_results.append(f"Task completed: {signal.summary}")

                # Then trigger user interaction
                handle_task_completion_interaction(
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

                        # Extract content from result (format: "Content of file '...':\n\n<content>")
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
                    import json as json_module

                    result_data = json_module.loads(result)
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
            tool_results.append(result)

            # Display tool success/failure (brief)
            if tool_success:
                console.print(f"[dim]✓ {tool_call.function.name} completed[/dim]")
            else:
                console.print(f"[yellow]⚠ {tool_call.function.name} completed with warnings/errors[/yellow]")

                # Add reflection on failure if enabled
                if enable_reflection and session.episodic_memory.current_episode:
                    session.episodic_memory.add_action_to_current_episode(
                        action_type="tool_call",
                        description=f"{tool_call.function.name}: {tool_call.function.arguments[:100]}...",
                        result=result[:200],
                        success=False
                    )
                    # Trigger reflection via agent (could enhance with explicit reflect tool call)

    return tool_results





def main_loop(context: AppContext) -> None:
    """
    Main application loop.

    Args:
        context: Application context with all dependencies
    """
    console = get_console()
    prompt_session = get_prompt_session()

    # Initialize session
    session = GrokSession(context.client, context.config, context.tool_executor)

    # Register task tools now that we have a session with task_manager
    from src.tools.task_tools import create_task_tools
    for tool in create_task_tools(context.config, session.task_manager):
        context.tool_executor.register_tool(tool)

    # Inject context manager into file tools to fix stale mount problem
    context.tool_executor.inject_context_manager(session.context_manager)

    # Main interaction loop
    while True:
        try:
            # Get user input
            conversation_history = session.get_conversation_history()
            prompt_indicator = get_prompt_indicator(conversation_history, session.model)
            user_input = prompt_session.prompt(f"{prompt_indicator} - Your message: ")

            if not user_input.strip():
                continue

            # Try to handle as command first
            command_result = context.command_registry.execute_command(user_input, session)
            if command_result:
                # Command was executed
                if not command_result.should_continue:
                    break
                continue

            # Check if input looks like an unknown command
            if user_input.strip().startswith("/") and len(user_input.strip().split()) == 1:
                # Try to find a similar command
                similar_cmd = context.command_registry.find_similar_command(user_input)
                if similar_cmd:
                    # Ask user if they meant the similar command
                    confirm = prompt_session.prompt(
                        f"⚠️  Unknown command. Did you mean '{similar_cmd}'? (y/N): ",
                        default="n"
                    ).strip().lower()

                    if confirm in ["y", "yes"]:
                        # Execute the suggested command
                        command_result = context.command_registry.execute_command(similar_cmd, session)
                        if command_result and not command_result.should_continue:
                            break
                        continue
                    else:
                        console.print("[yellow]Treating as a message to the AI.[/yellow]")
                else:
                    # No similar command found - warn and ask
                    console.print(f"[yellow]⚠️  Unknown command: {user_input}[/yellow]")
                    console.print("[dim]Type /help to see available commands.[/dim]")
                    confirm = prompt_session.prompt(
                        "Send this as a message to the AI instead? (y/N): ",
                        default="n"
                    ).strip().lower()

                    if confirm not in ["y", "yes"]:
                        continue  # Don't send to AI, just continue loop

            # Add user message to session (this starts a turn)
            session.add_message("user", user_input)

            try:
                # Show thinking indicator
                display_thinking_indicator()

                # Get AI response (check if one-time reasoner is requested)
                response = session.get_response()

                # Multi-step reasoning loop: Continue until no more tool calls
                step_count = 0
                max_steps = context.config.max_reasoning_steps

                while (
                    hasattr(response, "tool_calls")
                    and response.tool_calls
                    and step_count < max_steps
                ):
                    step_count += 1

                    # Display assistant response if it has content (before tool calls)
                    if hasattr(response, "content") and response.content:
                        display_assistant_response(
                            response.content,
                            enable_markdown=context.config.enable_markdown_rendering,
                            code_theme=context.config.markdown_code_theme
                        )

                    # Handle the current batch of tool calls (with interrupt handling)
                    try:
                        handle_tool_calls(response, context.tool_executor, session)
                    except KeyboardInterrupt:
                        console.print("\n[yellow]⚠️  Tool execution interrupted by user (Ctrl+C).[/yellow]")
                        console.print("[dim]Stopping current operation...[/dim]")
                        raise  # Re-raise to outer handler

                    # Get the next response from the model to analyze tool results
                    if step_count < max_steps:
                        console.print(f"[dim]Step {step_count}: Analyzing tool results...[/dim]")
                        display_thinking_indicator()
                        response = session.get_response()
                    else:
                        if max_steps < 999999:  # Don't show warning if effectively unlimited
                            console.print(
                                f"[yellow]Maximum reasoning steps ({max_steps}) reached. Use --max-steps to increase.[/yellow]"
                            )
                        break

                # Display completion summary if multi-step reasoning occurred
                if step_count > 0:
                    console.print(
                        f"[dim]Completed reasoning in {step_count} step{'s' if step_count != 1 else ''}.[/dim]"
                    )

                # Display final response (without tool calls)
                if hasattr(response, "content") and response.content:
                    display_assistant_response(
                        response.content,
                        enable_markdown=context.config.enable_markdown_rendering,
                        code_theme=context.config.markdown_code_theme
                    )

                # Complete the turn successfully
                session.complete_turn("AI interaction completed")

            except Exception as e:
                # Complete the turn even on error to avoid leaving it dangling
                session.complete_turn(f"AI interaction failed: {str(e)}")
                raise  # Re-raise the exception to be handled by outer try-catch

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Interrupted by user (Ctrl+C).[/yellow]")
            console.print("[dim]Press Ctrl+C again to exit, or continue typing...[/dim]")
            # Complete the current turn if one is active
            with contextlib.suppress(BaseException):
                session.complete_turn("Interrupted by user")
            continue  # Continue the loop instead of breaking
        except EOFError:
            console.print("\n[yellow]EOF received, exiting.[/yellow]")
            break
        except Exception as e:
            display_error(f"Unexpected error: {str(e)}")
            console.print("[dim]Please try again or use /help for assistance.[/dim]")


def one_shot_mode(prompt: str, context: AppContext) -> None:
    """
    Execute a single prompt and exit.

    Args:
        prompt: User prompt to execute
        context: Application context with all dependencies
    """
    get_console()

    try:
        # Initialize session
        session = GrokSession(context.client, context.config, context.tool_executor)

        # Register task tools now that we have a session with task_manager
        from src.tools.task_tools import create_task_tools
        for tool in create_task_tools(context.config, session.task_manager):
            context.tool_executor.register_tool(tool)

        # Inject context manager into file tools to fix stale mount problem
        context.tool_executor.inject_context_manager(session.context_manager)

        # Add user message to session
        session.start_turn(prompt)

        # Get AI response
        response = session.get_response()

        # Multi-step reasoning loop
        step_count = 0
        max_steps = context.config.max_reasoning_steps

        while hasattr(response, "tool_calls") and response.tool_calls and step_count < max_steps:
            step_count += 1

            # Display assistant response if it has content
            if hasattr(response, "content") and response.content:
                display_assistant_response(
                    response.content,
                    enable_markdown=context.config.enable_markdown_rendering,
                    code_theme=context.config.markdown_code_theme
                )

            # Handle tool calls
            handle_tool_calls(response, context.tool_executor, session)

            # Get next response
            if step_count < max_steps:
                response = session.get_response()

        # Display final response
        if hasattr(response, "content") and response.content:
            display_assistant_response(
                response.content,
                enable_markdown=context.config.enable_markdown_rendering,
                code_theme=context.config.markdown_code_theme
            )

        # Complete the turn
        session.complete_turn("One-shot prompt completed")

    except Exception as e:
        display_error(f"Error processing prompt: {str(e)}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    console = get_console()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Grok CLI - AI assistant powered by xAI with advanced agentic reasoning",
        epilog="Examples:\n"
        "  grok-cli                                       # Interactive mode\n"
        '  grok-cli "create a Python script..."          # One-shot mode\n'
        '  grok-cli -r "explain recursion"               # Use reasoning model (short flag)\n'
        '  grok-cli --reasoner "complex analysis"        # Use reasoning model (long flag)\n'
        '  grok-cli --max "analyze large codebase"       # Enable 2M context\n'
        '  grok-cli --sequential "long conversation"     # Cache-optimized context mode\n'
        '  grok-cli --smart "memory efficient task"      # Smart truncation mode (default)\n'
        '  grok-cli --self "create a useful tool"        # Enable self-evolving mode\n'
        '  grok-cli --max-steps 0 "complex task"         # Unlimited tool calls\n'
        '  grok-cli --agent -r "autonomous task"         # Agent mode + reasoning\n'
        '  grok-cli --self --agent "create and test"     # Self-evolving + agent mode\n'
        '  grok-cli --agent --max-steps 0 "unlimited"    # Agent + unlimited steps\n'
        '  grok-cli --window-size 5 "long task"          # Keep 5 recent turns in context\n'
        '\n'
        'Agentic Reasoning:\n'
        '  grok-cli --episodes                            # Show recent task episodes and exit\n'
        '  grok-cli --episodes 20                         # Show last 20 episodes\n'
        '  grok-cli --improve                             # Show improvement suggestions and exit\n'
        '  grok-cli --plan "Refactor auth system"         # Start with structured planning\n'
        '  grok-cli --orchestrate "Complex project"       # Multi-agent orchestration\n'
        '  grok-cli --agent --plan "Autonomous planning"  # Agent + planning mode',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "prompt", nargs="?", help="Prompt to execute (if not provided, starts interactive mode)"
    )
    parser.add_argument(
        "-r", "--reasoner", action="store_true", help="Use the reasoning model for this request"
    )
    parser.add_argument(
        "--max", action="store_true", help="Enable extended 2M token context (Grok 4.1 models)"
    )
    parser.add_argument(
        "--agent", action="store_true", help="Enable agentic mode (autonomous shell execution without confirmations)"
    )
    parser.add_argument(
        "--self", action="store_true", dest="self_mode", help="Enable self-evolving mode (AI can create custom tools)"
    )
    parser.add_argument(
        "--max-steps", type=int, default=None, metavar="N",
        help="Maximum reasoning steps (tool call iterations). Default: 100, use 0 for unlimited"
    )
    parser.add_argument(
        "--window-size", type=int, default=None, metavar="N",
        help="Number of recent turns to preserve in sliding window (default: 3)"
    )

    # Agentic reasoning options
    parser.add_argument(
        "--episodes", nargs="?", const=10, type=int, metavar="N",
        help="Show recent task episodes (default: 10) and exit"
    )
    parser.add_argument(
        "--improve", action="store_true",
        help="Analyze past episodes and show improvement suggestions, then exit"
    )
    parser.add_argument(
        "--plan", action="store_true",
        help="Start with planning mode for the given prompt (requires prompt argument)"
    )
    parser.add_argument(
        "--orchestrate", action="store_true",
        help="Use multi-agent orchestration for the given prompt (requires prompt argument)"
    )

    # Context mode options (mutually exclusive)
    context_mode_group = parser.add_mutually_exclusive_group()
    context_mode_group.add_argument(
        "--sequential", action="store_true", help="Use cache-optimized context mode (preserves history longer)"
    )
    context_mode_group.add_argument(
        "--smart", action="store_true", help="Use smart truncation context mode (summarizes at 70%% usage, default)"
    )

    args = parser.parse_args()

    try:
        # Initialize application with AppContext
        context = initialize_application()

        # Apply command-line options
        if args.max:
            context.config.use_extended_context = True

        if args.reasoner:
            context.config.set_model(context.config.reasoner_model)

        if args.agent:
            context.config.agent_mode = True

        if args.self_mode:
            context.config.self_mode = True

        if args.max_steps is not None:
            context.config.max_reasoning_steps = args.max_steps if args.max_steps > 0 else 999999

        if args.window_size is not None:
            context.config.min_preserved_turns = args.window_size

        if args.sequential:
            context.config.initial_context_mode = "cache_optimized"

        if args.smart:
            context.config.initial_context_mode = "smart_truncation"

        # Handle agentic reasoning flags that show info and exit
        if args.episodes is not None:
            # Show episodes and exit
            from src.commands.agentic_commands import EpisodesCommand
            session = GrokSession(context.client, context.config)
            session.tool_executor = context.tool_executor
            cmd = EpisodesCommand(context.config)
            cmd.execute(session, str(args.episodes))
            sys.exit(0)

        if args.improve:
            # Show improvement suggestions and exit
            from src.commands.agentic_commands import ImproveCommand
            session = GrokSession(context.client, context.config)
            session.tool_executor = context.tool_executor
            cmd = ImproveCommand(context.config)
            cmd.execute(session, "")
            sys.exit(0)

        # Handle planning and orchestration flags (require prompt)
        if args.plan and not args.prompt:
            console.print("[red]Error: --plan requires a prompt argument[/red]")
            console.print("[dim]Example: grok-cli --plan \"Refactor the authentication system\"[/dim]")
            sys.exit(1)

        if args.orchestrate and not args.prompt:
            console.print("[red]Error: --orchestrate requires a prompt argument[/red]")
            console.print("[dim]Example: grok-cli --orchestrate \"Build a complete API with tests\"[/dim]")
            sys.exit(1)

        # Check if running in one-shot mode or interactive mode
        if args.prompt:
            # Modify prompt for planning or orchestration
            modified_prompt = args.prompt
            if args.plan:
                modified_prompt = f"Use the generate_plan tool to create a detailed plan for: {args.prompt}"
            elif args.orchestrate:
                modified_prompt = f"Use the orchestrate tool to coordinate multiple agents for: {args.prompt}"

            # One-shot mode: execute prompt and exit
            one_shot_mode(modified_prompt, context)
        else:
            # Interactive mode: start REPL
            display_startup_banner()
            main_loop(context)

    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        display_error(f"Failed to initialize application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
