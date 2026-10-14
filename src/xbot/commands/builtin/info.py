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
            cmd_table.add_row("/login, /auth", "Config", "Authenticate with an LLM provider and pick default model")
            cmd_table.add_row("/model, /m", "Config", "View or switch active model (provider/model_id)")
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
    """Display and manage active agent settings and provider configuration."""

    name = "config"
    aliases = ["settings"]
    description = "Display and update provider, model, and environment settings"
    usage = "/config [get <key> | set <key> <value> [--global|--project] | path]"
    category = "Config"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        from InquirerPy.base.control import Choice
        from xbot.config import (
            get_config_file_paths,
            normalize_setting_key,
            update_setting,
        )

        args = list(context.args)
        config = context.agent_manager.config
        global_path, project_path = get_config_file_paths(
            base_path=config.workspace_dir, data_dir=config.data_dir
        )

        # Subcommand: path
        if args and args[0].lower() == "path":
            g_status = "[green]exists[/green]" if global_path.is_file() else "[dim]not created yet[/dim]"
            p_status = "[green]exists[/green]" if project_path.is_file() else "[dim]not created yet[/dim]"
            context.console.print(
                Panel(
                    f"[bold yellow]Global Settings:[/bold yellow] [cyan]{global_path}[/cyan] ({g_status})\n"
                    f"[bold yellow]Project Settings:[/bold yellow] [cyan]{project_path}[/cyan] ({p_status})",
                    title="[bold cyan]Config File Paths[/bold cyan]",
                    box=box.ROUNDED,
                )
            )
            context.console.print()
            return CommandResult(handled=True)

        # Subcommand: get <key>
        if args and args[0].lower() == "get":
            if len(args) < 2:
                context.console.print("[bold red]Usage:[/bold red] /config get <key>\n")
                return CommandResult(handled=True)

            raw_key = args[1]
            key = normalize_setting_key(raw_key)
            val = None
            if hasattr(config, "__dataclass_fields__"):
                if key in config.__dataclass_fields__:
                    val = getattr(config, key)
            else:
                from unittest.mock import MagicMock
                candidate = getattr(config, key, None)
                if candidate is not None and not isinstance(candidate, MagicMock):
                    val = candidate

            if val is None and hasattr(config, "raw_settings") and isinstance(config.raw_settings, dict):
                val = config.raw_settings.get(key)

            if val is not None:
                context.console.print(f"[bold cyan]{key}[/bold cyan] = [bright_white]{val}[/bright_white]\n")
            else:
                context.console.print(f"[yellow]Setting '{raw_key}' not found or not configured.[/yellow]\n")
            return CommandResult(handled=True)

        # Subcommand: set <key> <value> [--global | --project]
        if args and args[0].lower() == "set":
            if len(args) >= 3:
                raw_key = args[1]
                key = normalize_setting_key(raw_key)
                val_parts = []
                scope = "global"

                for part in args[2:]:
                    if part.lower() in ("--project", "-p"):
                        scope = "project"
                    elif part.lower() in ("--global", "-g"):
                        scope = "global"
                    else:
                        val_parts.append(part)

                val = " ".join(val_parts)
                new_cfg = update_setting(
                    key=key,
                    value=val,
                    scope=scope,
                    base_path=config.workspace_dir,
                    data_dir=config.data_dir,
                )
                context.agent_manager.update_config(new_cfg)
                target_path = project_path if scope == "project" else global_path
                context.console.print(
                    f"\n[bold green]✓ Updated[/bold green] [bold cyan]{key}[/bold cyan] to "
                    f"[bright_white]'{val}'[/bright_white] in [dim]{target_path}[/dim]\n"
                )
                context.console.print(create_config_table(new_cfg))
                context.console.print()
                return CommandResult(handled=True)
            elif len(args) == 2:
                # Key provided, prompt for value interactively
                key = normalize_setting_key(args[1])
                await self._interactive_update(context, default_key=key)
                return CommandResult(handled=True)
            else:
                await self._interactive_update(context)
                return CommandResult(handled=True)

        # Default: display config table
        context.console.print(create_config_table(config))
        context.console.print()

        # If interactive TUI is active and no subcommands were passed, offer action menu
        if context.tui is not None and not args:
            action = await context.select(
                message="Config Actions:",
                choices=[
                    Choice(name="1. Done (Close)", value="done"),
                    Choice(name="2. Update a setting", value="update"),
                    Choice(name="3. Show config file paths", value="path"),
                ],
                default="done",
            )
            if action == "update":
                await self._interactive_update(context)
            elif action == "path":
                g_status = "[green]exists[/green]" if global_path.is_file() else "[dim]not created yet[/dim]"
                p_status = "[green]exists[/green]" if project_path.is_file() else "[dim]not created yet[/dim]"
                context.console.print(
                    Panel(
                        f"[bold yellow]Global Settings:[/bold yellow] [cyan]{global_path}[/cyan] ({g_status})\n"
                        f"[bold yellow]Project Settings:[/bold yellow] [cyan]{project_path}[/cyan] ({p_status})",
                        title="[bold cyan]Config File Paths[/bold cyan]",
                        box=box.ROUNDED,
                    )
                )
                context.console.print()

        return CommandResult(handled=True)

    async def _interactive_update(
        self, context: CommandContext, default_key: Optional[str] = None
    ) -> None:
        """Guide the user through interactively updating or creating a config key."""
        from InquirerPy.base.control import Choice
        from xbot.config import (
            get_config_file_paths,
            normalize_setting_key,
            update_setting,
        )

        config = context.agent_manager.config
        global_path, project_path = get_config_file_paths(
            base_path=config.workspace_dir, data_dir=config.data_dir
        )

        target_key = default_key
        if not target_key:
            key_choices = [
                Choice(name=f"model_id (Current: {config.model_id})", value="model_id"),
                Choice(name=f"api_key (Current: {config.masked_api_key})", value="api_key"),
                Choice(name=f"base_url (Current: {config.base_url})", value="base_url"),
                Choice(name=f"tinyfish_api_key (Current: {config.masked_tinyfish_key})", value="tinyfish_api_key"),
                Choice(name=f"bash_timeout (Current: {config.bash_timeout}s)", value="bash_timeout"),
                Choice(name=f"temperature (Current: {config.temperature})", value="temperature"),
                Choice(name="Custom / Other key...", value="__custom__"),
            ]
            selected_key = await context.select(
                message="Select setting to update or create:",
                choices=key_choices,
                default="model_id",
            )
            if not selected_key:
                return

            if selected_key == "__custom__":
                custom_input = await context.ask("Enter configuration key name:")
                if not custom_input or not custom_input.strip():
                    return
                target_key = normalize_setting_key(custom_input)
            else:
                target_key = selected_key

        scope_choices = [
            Choice(name=f"Global (~/.xbot/settings.json)", value="global"),
            Choice(name=f"Project (.xbot/settings.json)", value="project"),
        ]
        chosen_scope = await context.select(
            message=f"Where should '{target_key}' be saved?",
            choices=scope_choices,
            default="global",
        )
        if not chosen_scope:
            return

        current_val = getattr(config, target_key, "")
        if current_val is None:
            current_val = ""

        default_prompt_val = "" if "key" in target_key else str(current_val)

        new_val = await context.ask(
            message=f"Enter value for '{target_key}':",
            default=default_prompt_val,
        )
        if new_val is None:
            return

        new_cfg = update_setting(
            key=target_key,
            value=new_val.strip(),
            scope=chosen_scope,
            base_path=config.workspace_dir,
            data_dir=config.data_dir,
        )
        context.agent_manager.update_config(new_cfg)
        target_path = project_path if chosen_scope == "project" else global_path
        context.console.print(
            f"\n[bold green]✓ Successfully updated[/bold green] [bold cyan]{target_key}[/bold cyan] in [dim]{target_path}[/dim]\n"
        )
        context.console.print(create_config_table(new_cfg))
        context.console.print()


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
