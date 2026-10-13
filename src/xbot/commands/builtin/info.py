"""Informational commands: /help, /config, /tools."""

from __future__ import annotations

from typing import Optional

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from xbot.commands.base import BaseCommand, CommandContext, CommandResult
from xbot.tools import TOOL_METADATA
from xbot.tui.components import create_config_table, create_tools_table


class HelpCommand(BaseCommand):
    """Display comprehensive help table with dynamically registered slash commands."""

    name = "help"
    aliases = ["?"]
    description = "Show available slash commands and registered tools"
    usage = "/help"
    category = "System"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        cmd_table = Table(title="[bold yellow]⚡ Slash Commands[/bold yellow]", box=box.ROUNDED)
        cmd_table.add_column("Command", style="bold cyan")
        cmd_table.add_column("Category", style="magenta")
        cmd_table.add_column("Description", style="white")

        commands: list[BaseCommand] = []
        if context.tui and hasattr(context.tui, "command_registry"):
            commands = context.tui.command_registry.all_commands()

        if commands:
            for cmd in commands:
                aliases_str = f" [dim]({', '.join('/' + a for a in cmd.aliases)})[/dim]" if cmd.aliases else ""
                trigger = f"/{cmd.name}{aliases_str}"
                cmd_table.add_row(trigger, cmd.category, cmd.description)
        else:
            # Fallback static listing
            cmd_table.add_row("/help, /?", "System", "Show this help table")
            cmd_table.add_row("/resume [all], /history", "Session", "Browse and resume past sessions")
            cmd_table.add_row("/new, /reset", "Session", "Start a new session")
            cmd_table.add_row("/tools", "Inspection", "List all available agent tools")
            cmd_table.add_row("/config, /settings", "Config", "Display active provider, model, and env settings")
            cmd_table.add_row("/clear, /cls", "System", "Clear terminal screen")
            cmd_table.add_row("/exit, /quit, /q", "System", "Exit the agent session")

        tool_table = Table(title="[bold yellow]🔧 Core Tools Available[/bold yellow]", box=box.ROUNDED)
        tool_table.add_column("Tool", style="bold green")
        tool_table.add_column("Role", style="white")

        for name, desc in TOOL_METADATA.items():
            tool_table.add_row(name, desc)

        panel = Panel(
            Group(cmd_table, Text(""), tool_table),
            box=box.ROUNDED,
            border_style="yellow",
            title="[bold]Help & Reference[/bold]",
        )
        context.console.print(panel)
        context.console.print()
        return CommandResult(handled=True)


class ConfigCommand(BaseCommand):
    """Display active agent settings and provider configuration."""

    name = "config"
    aliases = ["settings"]
    description = "Display active provider, model, and environment settings"
    usage = "/config"
    category = "Config"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        context.console.print(create_config_table(context.agent_manager.config))
        context.console.print()
        return CommandResult(handled=True)


class ToolsCommand(BaseCommand):
    """List all available tools and parameters."""

    name = "tools"
    aliases = []
    description = "List all available agent tools and parameters"
    usage = "/tools"
    category = "Inspection"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        context.console.print(create_tools_table())
        context.console.print()
        return CommandResult(handled=True)
