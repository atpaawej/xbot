"""System termination command: /exit."""

from __future__ import annotations

from typing import Optional

from xbot.commands.base import BaseCommand, CommandContext, CommandResult


class ExitCommand(BaseCommand):
    """Exit the xbot session."""

    name = "exit"
    aliases = ["quit", "q"]
    description = "Exit the agent session"
    usage = "/exit"
    category = "System"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        context.console.print("\n[bold yellow]👋 Farewell from xbot![/bold yellow]\n")
        return CommandResult(should_exit=True, handled=True)
