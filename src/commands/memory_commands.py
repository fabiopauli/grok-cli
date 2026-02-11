#!/usr/bin/env python3

"""
Memory management commands for Grok Assistant

Interactive memory management with clean command structure.
"""

from rich.table import Table

from ..core.session import GrokSession
from .base import BaseCommand, CommandResult


class MemoryCommand(BaseCommand):
    """Interactive memory management command."""

    def get_pattern(self) -> str:
        return "/memory"

    def get_description(self) -> str:
        return "Interactive memory management"

    def matches(self, user_input: str) -> bool:
        return user_input.strip().lower() == "/memory"

    def execute(self, user_input: str, session: GrokSession) -> CommandResult:
        """Execute the interactive memory command."""
        from ..ui.console import get_console, get_prompt_session

        console = get_console()
        prompt_session = get_prompt_session()
        memory_manager = session.get_memory_manager()

        while True:
            # Display memory management menu
            console.print("\n[bold cyan]Memory Management[/bold cyan]")
            console.print("1. List memories (current directory + global)")
            console.print("2. List global memories only")
            console.print("3. List directory memories only")
            console.print("4. Save new memory")
            console.print("5. Remove memory")
            console.print("6. Clear all memories")
            console.print("7. Import memories from another directory")
            console.print("8. Export memories")
            console.print("9. Memory statistics")
            console.print("q. Quit")

            choice = prompt_session.prompt("\nChoose option (1-9) or 'q' to quit: ").strip().lower()

            if choice == 'q' or choice == 'quit':
                break
            elif choice == '1':
                self._list_all_memories(console, memory_manager)
            elif choice == '2':
                self._list_global_memories(console, memory_manager)
            elif choice == '3':
                self._list_directory_memories(console, memory_manager)
            elif choice == '4':
                self._save_new_memory(console, prompt_session, memory_manager)
            elif choice == '5':
                self._remove_memory(console, prompt_session, memory_manager)
            elif choice == '6':
                self._clear_memories(console, prompt_session, memory_manager)
            elif choice == '7':
                self._import_memories(console, prompt_session, memory_manager)
            elif choice == '8':
                self._export_memories(console, memory_manager)
            elif choice == '9':
                self._show_statistics(console, memory_manager)
            else:
                console.print("[red]Invalid choice. Please try again.[/red]")

        return CommandResult.ok()

    def _list_all_memories(self, console, memory_manager) -> None:
        """List all memories (global + directory)."""
        memories = memory_manager.get_all_memories()

        if not memories:
            console.print("[yellow]No memories found.[/yellow]")
            return

        table = Table(title="All Memories", show_header=True, header_style="bold bright_blue")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Scope", style="yellow")
        table.add_column("Content", style="white")
        table.add_column("Created", style="dim")

        for memory in memories:
            table.add_row(
                memory.get("id", ""),
                memory.get("type", "").replace("_", " ").title(),
                memory.get("scope", "directory"),
                memory.get("content", "")[:50] + "..." if len(memory.get("content", "")) > 50 else memory.get("content", ""),
                memory.get("created", "")[:10] if memory.get("created") else ""
            )

        console.print(table)

    def _list_global_memories(self, console, memory_manager) -> None:
        """List global memories only."""
        memories = memory_manager.get_global_memories()

        if not memories:
            console.print("[yellow]No global memories found.[/yellow]")
            return

        table = Table(title="Global Memories", show_header=True, header_style="bold bright_blue")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Content", style="white")
        table.add_column("Created", style="dim")

        for memory in memories:
            table.add_row(
                memory.get("id", ""),
                memory.get("type", "").replace("_", " ").title(),
                memory.get("content", "")[:60] + "..." if len(memory.get("content", "")) > 60 else memory.get("content", ""),
                memory.get("created", "")[:10] if memory.get("created") else ""
            )

        console.print(table)

    def _list_directory_memories(self, console, memory_manager) -> None:
        """List directory memories only."""
        memories = memory_manager.get_directory_memories()

        if not memories:
            console.print("[yellow]No directory memories found.[/yellow]")
            return

        table = Table(title=f"Directory Memories ({memory_manager.current_directory})",
                     show_header=True, header_style="bold bright_blue")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Content", style="white")
        table.add_column("Created", style="dim")

        for memory in memories:
            table.add_row(
                memory.get("id", ""),
                memory.get("type", "").replace("_", " ").title(),
                memory.get("content", "")[:60] + "..." if len(memory.get("content", "")) > 60 else memory.get("content", ""),
                memory.get("created", "")[:10] if memory.get("created") else ""
            )

        console.print(table)

    def _save_new_memory(self, console, prompt_session, memory_manager) -> None:
        """Save a new memory."""
        console.print("\n[bold]Save New Memory[/bold]")

        # Get memory content
        content = prompt_session.prompt("Memory content: ").strip()
        if not content:
            console.print("[red]Memory content cannot be empty.[/red]")
            return

        # Get memory type
        console.print("\nMemory types:")
        console.print("1. user_preference - User's preferred tools/patterns")
        console.print("2. architectural_decision - Project structure/tech choices")
        console.print("3. important_fact - Critical project information")
        console.print("4. project_context - Specific constraints/requirements")

        type_choice = prompt_session.prompt("Choose type (1-4): ").strip()
        type_map = {
            "1": "user_preference",
            "2": "architectural_decision",
            "3": "important_fact",
            "4": "project_context"
        }

        if type_choice not in type_map:
            console.print("[red]Invalid type choice.[/red]")
            return

        memory_type = type_map[type_choice]

        # Get scope
        scope_choice = prompt_session.prompt("Scope - (d)irectory or (g)lobal [d]: ").strip().lower()
        scope = "global" if scope_choice.startswith('g') else "directory"

        # Save memory
        try:
            memory_id = memory_manager.save_memory(content, memory_type, scope)
            scope_text = "globally" if scope == "global" else "for current directory"
            console.print(f"[green]✓ Saved {memory_type.replace('_', ' ').title()} {scope_text}: {content}[/green]")
            console.print(f"[dim]Memory ID: {memory_id}[/dim]")
        except Exception as e:
            console.print(f"[red]Failed to save memory: {str(e)}[/red]")

    def _remove_memory(self, console, prompt_session, memory_manager) -> None:
        """Remove a memory."""
        console.print("\n[bold]Remove Memory[/bold]")

        # Show current memories for reference
        memories = memory_manager.get_all_memories()
        if not memories:
            console.print("[yellow]No memories to remove.[/yellow]")
            return

        console.print("Current memories:")
        for memory in memories[-10:]:  # Show last 10
            console.print(f"  {memory.get('id', '')}: {memory.get('content', '')[:50]}...")

        memory_id = prompt_session.prompt("\nMemory ID to remove: ").strip()
        if not memory_id:
            console.print("[red]Memory ID cannot be empty.[/red]")
            return

        # Confirm removal
        confirm = prompt_session.prompt(f"Are you sure you want to remove memory '{memory_id}'? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            console.print("[yellow]Removal cancelled.[/yellow]")
            return

        # Remove memory
        success = memory_manager.remove_memory(memory_id)
        if success:
            console.print(f"[green]✓ Removed memory: {memory_id}[/green]")
        else:
            console.print(f"[red]Memory not found: {memory_id}[/red]")

    def _clear_memories(self, console, prompt_session, memory_manager) -> None:
        """Clear memories."""
        console.print("\n[bold]Clear Memories[/bold]")
        console.print("1. Clear directory memories")
        console.print("2. Clear global memories")
        console.print("3. Clear all memories")

        choice = prompt_session.prompt("Choose option (1-3): ").strip()

        if choice == "1":
            count = len(memory_manager.get_directory_memories())
            if count == 0:
                console.print("[yellow]No directory memories to clear.[/yellow]")
                return

            confirm = prompt_session.prompt(f"Clear {count} directory memories? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                cleared = memory_manager.clear_directory_memories()
                console.print(f"[green]✓ Cleared {cleared} directory memories[/green]")

        elif choice == "2":
            count = len(memory_manager.get_global_memories())
            if count == 0:
                console.print("[yellow]No global memories to clear.[/yellow]")
                return

            confirm = prompt_session.prompt(f"Clear {count} global memories? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                cleared = memory_manager.clear_global_memories()
                console.print(f"[green]✓ Cleared {cleared} global memories[/green]")

        elif choice == "3":
            total_count = len(memory_manager.get_all_memories())
            if total_count == 0:
                console.print("[yellow]No memories to clear.[/yellow]")
                return

            confirm = prompt_session.prompt(f"Clear ALL {total_count} memories? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                dir_cleared = memory_manager.clear_directory_memories()
                global_cleared = memory_manager.clear_global_memories()
                console.print(f"[green]✓ Cleared {dir_cleared + global_cleared} total memories[/green]")

        else:
            console.print("[red]Invalid choice.[/red]")

    def _import_memories(self, console, prompt_session, memory_manager) -> None:
        """Import memories from another directory."""
        import json
        from pathlib import Path

        console.print("\n[bold]Import Memories[/bold]")

        dir_path = prompt_session.prompt("Directory path to import from: ").strip()
        if not dir_path:
            console.print("[red]Directory path cannot be empty.[/red]")
            return

        try:
            source_dir = Path(dir_path).resolve()
            if not source_dir.exists():
                console.print(f"[red]Directory does not exist: {source_dir}[/red]")
                return

            memory_file = source_dir / ".grok_memory.json"
            if not memory_file.exists():
                console.print(f"[red]No memory file found in: {source_dir}[/red]")
                return

            # Load memories from file
            with open(memory_file, encoding='utf-8') as f:
                data = json.load(f)

            memories = data.get("memories", [])
            if not memories:
                console.print("[yellow]No memories found in the file.[/yellow]")
                return

            console.print(f"Found {len(memories)} memories to import")

            # Choose merge or replace
            merge_choice = prompt_session.prompt("(m)erge with existing or (r)eplace existing? [m]: ").strip().lower()
            merge = not merge_choice.startswith('r')

            # Import memories
            import_data = {"directory_memories": {str(memory_manager.current_directory): memories}}
            stats = memory_manager.import_memories(import_data, merge=merge)

            console.print(f"[green]✓ Imported {stats['directory_imported']} memories[/green]")

        except Exception as e:
            console.print(f"[red]Failed to import memories: {str(e)}[/red]")

    def _export_memories(self, console, memory_manager) -> None:
        """Export memories."""
        import json
        from datetime import datetime

        console.print("\n[bold]Export Memories[/bold]")

        try:
            export_data = memory_manager.export_memories()

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"grok_memories_export_{timestamp}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            total_memories = len(export_data.get("global_memories", [])) + \
                           sum(len(memories) for memories in export_data.get("directory_memories", {}).values())

            console.print(f"[green]✓ Exported {total_memories} memories to {filename}[/green]")

        except Exception as e:
            console.print(f"[red]Failed to export memories: {str(e)}[/red]")

    def _show_statistics(self, console, memory_manager) -> None:
        """Show memory statistics."""

        stats = memory_manager.get_memory_statistics()

        table = Table(title="Memory Statistics", show_header=True, header_style="bold bright_blue")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Global Memories", str(stats["global_memories"]))
        table.add_row("Current Directory Memories", str(stats["current_directory_memories"]))
        table.add_row("Total Directory Memories", str(stats["total_directory_memories"]))
        table.add_row("Directories with Memories", str(stats["total_directories_with_memories"]))
        table.add_row("Total Memories", str(stats["total_memories"]))
        table.add_row("Current Directory", str(stats["current_directory"]))

        console.print(table)

        # Show memory types breakdown
        if stats["memory_types"]:
            console.print("\n[bold]Memory Types:[/bold]")
            for memory_type, count in stats["memory_types"].items():
                type_name = memory_type.replace("_", " ").title()
                console.print(f"  {type_name}: {count}")
