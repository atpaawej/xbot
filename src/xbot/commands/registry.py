"""Command registry and dispatcher for slash commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from rich.console import Console

from xbot.commands.base import BaseCommand, CommandContext, CommandResult

if TYPE_CHECKING:
    from xbot.agent import AgentManager


class CommandRegistry:
    """Registry maintaining available slash commands and handling execution dispatch."""

    def __init__(self) -> None:
        self._commands: dict[str, BaseCommand] = {}
        self._unique_commands: list[BaseCommand] = []

    def register(self, command: BaseCommand) -> None:
        """Register a command under its primary name and all aliases."""
        clean_name = command.name.lstrip("/").lower()
        self._commands[clean_name] = command

        for alias in command.aliases:
            clean_alias = alias.lstrip("/").lower()
            self._commands[clean_alias] = command

        if command not in self._unique_commands:
            self._unique_commands.append(command)

    def get(self, name: str) -> Optional[BaseCommand]:
        """Retrieve a command by primary name or alias."""
        clean_name = name.lstrip("/").lower()
        return self._commands.get(clean_name)

    def all_commands(self) -> list[BaseCommand]:
        """Return all registered unique command instances."""
        return list(self._unique_commands)

    def find(self, query: str) -> list[BaseCommand]:
        """Search commands matching prefix or substring query across names and descriptions."""
        clean_query = query.lstrip("/").lower()
        if not clean_query:
            return self.all_commands()

        matches: list[BaseCommand] = []
        for cmd in self._unique_commands:
            cmd_name = cmd.name.lstrip("/").lower()
            aliases = [a.lstrip("/").lower() for a in cmd.aliases]
            desc = cmd.description.lower()

            if (
                clean_query in cmd_name
                or any(clean_query in a for a in aliases)
                or clean_query in desc
            ):
                matches.append(cmd)

        return matches

    async def dispatch(
        self,
        raw_input: str,
        console: Console,
        agent_manager: AgentManager,
        tui: Optional[Any] = None,
    ) -> CommandResult:
        """Parse raw input, locate command, and execute with context."""
        trimmed = raw_input.strip()
        if not trimmed.startswith("/"):
            return CommandResult(handled=False)

        parts = trimmed.split(maxsplit=1)
        command_trigger = parts[0]
        raw_args = parts[1] if len(parts) > 1 else ""

        cmd_name = command_trigger.lstrip("/").lower()
        command = self.get(cmd_name)

        if not command:
            console.print(
                f"[bold red]Unknown command:[/bold red] /{cmd_name}. Type [cyan]/help[/cyan] for assistance.\n"
            )
            return CommandResult(handled=False)

        context = CommandContext.create(
            console=console,
            agent_manager=agent_manager,
            raw_args=raw_args,
            tui=tui,
        )

        try:
            result = await command.execute(context)
            if result is None:
                return CommandResult(handled=True)
            return result
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Command cancelled.[/dim]\n")
            return CommandResult(handled=True)
        except Exception as exc:
            console.print(f"\n[bold red]Command error in /{cmd_name}:[/bold red] {exc}\n")
            return CommandResult(handled=True)
