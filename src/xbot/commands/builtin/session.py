"""Session management commands: /new and /clear."""

from __future__ import annotations

from typing import Optional

from xbot.commands.base import BaseCommand, CommandContext, CommandResult
from xbot.tui.components import create_banner


class NewCommand(BaseCommand):
    """Start a fresh agent session."""

    name = "new"
    aliases = ["reset"]
    description = "Start a fresh session"
    usage = "/new"
    category = "Session"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        context.agent_manager.reset()
        context.console.print("[bold green]✓ Started a new session.[/bold green]\n")
        return CommandResult(handled=True)


class ClearCommand(BaseCommand):
    """Clear terminal screen and reprint banner."""

    name = "clear"
    aliases = ["cls"]
    description = "Clear terminal screen and display banner"
    usage = "/clear"
    category = "System"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        context.console.clear()
        if context.tui and hasattr(context.tui, "print_banner"):
            context.tui.print_banner()
        else:
            curr_title = (
                context.agent_manager.current_session.title
                if context.agent_manager.current_session
                else "New Session"
            )
            context.console.print(
                create_banner(context.agent_manager.config, session_title=curr_title)
            )
            context.console.print()
        return CommandResult(handled=True)
