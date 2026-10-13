"""Resume command for interactive and direct session switching."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from InquirerPy.base.control import Choice

from xbot.commands.base import BaseCommand, CommandContext, CommandResult


class ResumeCommand(BaseCommand):
    """Browse, search, and resume past agent sessions."""

    name = "resume"
    aliases = ["history"]
    description = "Browse and resume a previous session"
    usage = "/resume [all | <# | session_id>]"
    category = "Session"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        active_proj = context.agent_manager.session_manager.active_project
        proj_name = active_proj.name if active_proj else None

        all_projects = "all" in [arg.lower() for arg in context.args]

        # Extract direct target argument if provided (excluding the 'all' flag)
        target_arg: Optional[str] = None
        for arg in context.args:
            if arg.lower() != "all":
                target_arg = arg
                break

        # Fast direct switch path (e.g. /resume 1 or /resume sess_123)
        if target_arg:
            sessions = context.agent_manager.session_manager.list_sessions(
                all_projects=all_projects, limit=100
            )
            target_id: Optional[str] = None

            if target_arg.isdigit():
                idx = int(target_arg)
                if 1 <= idx <= len(sessions):
                    target_id = sessions[idx - 1].id
                else:
                    context.console.print(
                        f"[bold red]Invalid session index #{idx}.[/bold red] Total available: {len(sessions)}.\n"
                    )
                    return CommandResult(handled=True)
            else:
                target_id = target_arg

            if target_id:
                success = context.agent_manager.load_session(target_id)
                if success:
                    curr = context.agent_manager.current_session
                    title = curr.title if curr else target_id
                    context.console.print(
                        f"[bold green]✓ Loaded session:[/bold green] [bold white]{title}[/bold white] ({target_id})\n"
                    )
                else:
                    context.console.print(f"[bold red]Session '{target_id}' not found.[/bold red]\n")
            return CommandResult(handled=True)

        # Interactive fuzzy picker path
        sessions = context.agent_manager.session_manager.list_sessions(
            all_projects=all_projects, limit=50
        )

        if not sessions:
            if not all_projects and proj_name:
                context.console.print(
                    f"[dim]No saved sessions found for project '{proj_name}'.[/dim]\n"
                    f"[dim]Tip: Use [/dim][cyan]/resume all[/cyan][dim] to browse sessions across all projects.[/dim]\n"
                )
            else:
                context.console.print("[dim]No saved sessions found. Start chatting to create one![/dim]\n")
            return CommandResult(handled=True)

        choices: list[Choice] = []
        for idx, s in enumerate(sessions, start=1):
            try:
                dt = datetime.fromisoformat(s.updated_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = s.updated_at[:16]

            proj_tag = f"[{getattr(s, 'project_name', None) or 'global'}]" if all_projects else ""
            display_text = f"#{idx:02d}  {s.title:<30}  {time_str}  {proj_tag}  ({s.id[:8]}...)"
            choices.append(Choice(name=display_text, value=s.id))

        prompt_title = (
            f"Select session to resume [{proj_name}]:"
            if proj_name and not all_projects
            else "Select session to resume [All Projects]:"
        )

        selected_id = await context.fuzzy_select(
            message=prompt_title,
            choices=choices,
        )

        if not selected_id:
            context.console.print("[dim]Session selection cancelled.[/dim]\n")
            return CommandResult(handled=True)

        success = context.agent_manager.load_session(selected_id)
        if success:
            curr = context.agent_manager.current_session
            title = curr.title if curr else selected_id
            context.console.print(
                f"[bold green]✓ Loaded session:[/bold green] [bold white]{title}[/bold white] ({selected_id})\n"
            )
        else:
            context.console.print(f"[bold red]Session '{selected_id}' not found.[/bold red]\n")

        return CommandResult(handled=True)
