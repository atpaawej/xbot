"""Rich UI components for xbot."""

from __future__ import annotations

import json
from typing import Any, Mapping

from rich import box
from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from xbot.config import Config
from xbot.tools import TOOL_METADATA
from xbot.tui.formatting import format_json, truncate_preview


def create_banner(config: Config, session_title: Optional[str] = None) -> Panel:
    """Render the startup banner with active configuration summary."""
    logo = Text()
    logo.append("  ██╗  ██╗██████╗  ██████╗ ████████╗\n", style="bold cyan")
    logo.append("  ╚██╗██╔╝██╔══██╗██╔═══██╗╚══██╔══╝\n", style="bold cyan")
    logo.append("   ╚███╔╝ ██████╔╝██║   ██║   ██║   \n", style="bold bright_cyan")
    logo.append("   ██╔██╗ ██╔══██╗██║   ██║   ██║   \n", style="bold blue")
    logo.append("  ██╔╝ ██╗██████╔╝╚██████╔╝   ██║   \n", style="bold blue")
    logo.append("  ╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   \n", style="dim")
    logo.append("  Autonomous AI Agent • AI SDK • TinyFish Web Intelligence\n", style="italic white")

    # Config summary table inside the banner
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold yellow")
    table.add_column("Value", style="bright_white")

    active_session = session_title or "New Session"
    table.add_row("Session", f"[bold bright_green]{active_session}[/bold bright_green]")
    table.add_row("Model", config.model_id)
    table.add_row("Provider URL", config.base_url)
    table.add_row("LLM Key", config.masked_api_key)

    tf_status = (
        "[bold green]Connected[/bold green]"
        if config.is_tinyfish_configured
        else "[bold red]Not Configured (Free at agent.tinyfish.ai)[/bold red]"
    )
    table.add_row("TinyFish", tf_status)
    table.add_row("Workspace", str(config.workspace_dir))

    cfg_files = getattr(config, "loaded_config_files", [])
    if cfg_files:
        files_str = ", ".join(f"[cyan]{f}[/cyan]" for f in cfg_files)
        table.add_row("Settings Files", files_str)

    if config.loaded_env_files:
        files_str = ", ".join(f"[cyan]{f}[/cyan]" for f in config.loaded_env_files)
        table.add_row("Env Files", files_str)
    elif not cfg_files:
        table.add_row("Config Files", "[dim]None (defaults / process environment)[/dim]")

    content = Group(
        Align.center(logo),
        Text("─" * 60, style="dim"),
        table,
        Text("Type prompt or /help. Use Alt+Enter for multi-line. Press Ctrl+C to cancel.", style="dim italic"),
    )

    return Panel(
        content,
        border_style="cyan",
        box=box.ROUNDED,
        title="[bold bright_white]🤖 xbot v0.1.0[/bold bright_white]",
        subtitle="[dim]Powered by Python AI SDK & TinyFish[/dim]",
        padding=(1, 2),
    )


def create_session_list_panel(
    sessions: list[Any],
    project_name: Optional[str] = None,
    show_project_col: bool = False,
) -> Panel:
    """Render interactive session list table without turns."""
    panel_title = (
        f"[bold cyan]Saved Sessions History — {project_name}[/bold cyan]"
        if project_name and not show_project_col
        else "[bold cyan]Saved Sessions History (All Projects)[/bold cyan]"
    )
    table = Table(box=box.ROUNDED, title=panel_title)
    table.add_column("[#]", style="bold yellow", justify="center", width=5)
    table.add_column("Title", style="bold white")
    if show_project_col:
        table.add_column("Project", style="magenta")
    table.add_column("Updated", style="cyan")
    table.add_column("Session ID", style="dim")

    for idx, s in enumerate(sessions, start=1):
        # Format updated timestamp cleanly
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(s.updated_at)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = s.updated_at[:16]

        row_items = [f"[{idx}]", s.title]
        if show_project_col:
            p_label = getattr(s, "project_name", None) or "global"
            row_items.append(p_label)
        row_items.extend([time_str, s.id])

        table.add_row(*row_items)

    hint_text = (
        "\nType session number (e.g. 1) or ID to switch, or press Enter to cancel."
        if show_project_col
        else "\nType session number (e.g. 1) or ID to switch, or Enter to cancel. (Use '/resume all' for all projects)"
    )
    hint = Text(hint_text, style="dim italic")
    return Panel(Group(table, hint), box=box.ROUNDED, border_style="cyan")


def create_help_table() -> Panel:
    """Render help table with slash commands and core tools."""
    cmd_table = Table(title="[bold yellow]⚡ Slash Commands[/bold yellow]", box=box.ROUNDED)
    cmd_table.add_column("Command", style="bold cyan")
    cmd_table.add_column("Description", style="white")

    cmd_table.add_row("/help, /?", "Show this help table")
    cmd_table.add_row("/resume [all], /history", "Browse and load past sessions (current project or all)")
    cmd_table.add_row("/new, /reset", "Start a new session")
    cmd_table.add_row("/tools", "List all 8 available tools and parameters")
    cmd_table.add_row("/config, /settings", "Display active provider, model, and env settings")
    cmd_table.add_row("/clear, /cls", "Clear terminal screen")
    cmd_table.add_row("/exit, /quit, /q", "Exit the agent session")

    tool_table = Table(title="[bold yellow]🔧 Core Tools Available[/bold yellow]", box=box.ROUNDED)
    tool_table.add_column("Tool", style="bold green")
    tool_table.add_column("Role", style="white")

    for name, desc in TOOL_METADATA.items():
        tool_table.add_row(name, desc)

    return Panel(
        Group(cmd_table, Text(""), tool_table),
        box=box.ROUNDED,
        border_style="yellow",
        title="[bold]Help & Reference[/bold]",
    )


def create_config_table(config: Config) -> Panel:
    """Render configuration table."""
    table = Table(box=box.ROUNDED, title="[bold cyan]Current Configuration[/bold cyan]")
    table.add_column("Setting", style="bold yellow")
    table.add_column("Value", style="bright_white")

    table.add_row("Base URL", config.base_url)
    table.add_row("Model ID", config.model_id)
    table.add_row("API Key", config.masked_api_key)
    table.add_row("TinyFish Key", config.masked_tinyfish_key)
    table.add_row("Workspace Dir", str(config.workspace_dir))
    table.add_row("Bash Timeout", f"{config.bash_timeout}s")
    table.add_row("Temperature", str(config.temperature))
    table.add_row("Global Data Dir", str(config.data_dir))
    cfg_files = getattr(config, "loaded_config_files", [])
    table.add_row(
        "Settings Files",
        ", ".join(cfg_files) or "[dim]None (~/.xbot/settings.json not found)[/dim]",
    )
    table.add_row("Loaded Env Files", ", ".join(config.loaded_env_files) or "[dim]None[/dim]")

    return Panel(table, box=box.ROUNDED, border_style="cyan")


def create_tools_table() -> Panel:
    """Render detailed tools table."""
    table = Table(box=box.ROUNDED, title="[bold green]Agent Registered Tools[/bold green]")
    table.add_column("Tool Name", style="bold green")
    table.add_column("Backend / Mechanism", style="cyan")
    table.add_column("Description", style="white")

    details = [
        ("bash", "Subprocess Shell", "Run bash commands in workspace directory with timeout"),
        ("write", "Filesystem", "Create or overwrite files, auto-creating directories"),
        ("edit", "Filesystem", "Exact search-and-replace block replacement in files"),
        ("read", "Filesystem", "Read file contents with line numbering and range slicing"),
        ("grep", "Regex / Walk", "Search regex pattern across files excluding build/git noise"),
        ("glob", "Path Pattern", "Search files matching wildcard paths"),
        ("web_search", "TinyFish Search API", "Fast, agent-optimized live web search results"),
        ("web_fetch", "TinyFish Fetch API", "Extract clean, noise-free markdown from dynamic URLs"),
    ]

    for name, backend, desc in details:
        table.add_row(name, backend, desc)

    return Panel(table, box=box.ROUNDED, border_style="green")


from xbot.tui.cards import (
    ThinkingDrawer,
    ToolCardState,
    ToolState,
    render_tool_card,
)


def create_tool_call_panel(tool_name: str, args: dict[str, Any]) -> Panel:
    """Render a polymorphic card for an outgoing tool call in RUNNING state."""
    state = ToolCardState(
        tool_name=tool_name,
        tool_call_id="call",
        args=args or {},
        state=ToolState.RUNNING,
    )
    return render_tool_card(state)


def create_tool_result_panel(
    tool_name: str, result: str, is_error: bool = False
) -> Panel:
    """Render a polymorphic card for a tool execution result."""
    state = ToolCardState(
        tool_name=tool_name,
        tool_call_id="result",
        args={},
        state=ToolState.ERROR if is_error else ToolState.SUCCESS,
        result=result,
        is_error=is_error,
    )
    return render_tool_card(state)

