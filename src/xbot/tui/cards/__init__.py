"""Polymorphic tool card dispatchers and exports."""

from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from xbot.tui.cards.base import ToolCardState, ToolState, truncate_tail
from xbot.tui.cards.bash import render_bash_card
from xbot.tui.cards.diff import render_diff_card
from xbot.tui.cards.files import (
    render_file_read_card,
    render_file_write_card,
    render_glob_card,
    render_grep_card,
)
from xbot.tui.cards.thinking import ThinkingDrawer
from xbot.tui.cards.web import render_web_fetch_card, render_web_search_card
from xbot.tui.formatting import format_json


def render_default_card(state: ToolCardState) -> Panel:
    """Fallback card renderer for custom or arbitrary tools."""
    title_text = Text()
    title_text.append("🔧 ", style="bold bright_blue")
    title_text.append(f"tool: {state.tool_name}", style="bold bright_white")

    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • running]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error:
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        status_pill.append(f" [✓ done • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []
    if state.args:
        content_items.append(format_json(state.args))

    if state.result:
        clean_res = state.result.strip()
        tail_body, omitted = truncate_tail(clean_res, max_lines=6)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} lines omitted ...]", style="dim italic"))
        content_items.append(Text("─" * 40, style="dim"))
        content_items.append(Text(tail_body))

    return Panel(
        Group(*content_items) if content_items else Text("Executing...", style="dim"),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )


def render_tool_card(state: ToolCardState) -> Panel:
    """Polymorphic dispatcher: maps tool name to the specialized card renderer."""
    name = (state.tool_name or "").lower().strip()

    if name == "bash":
        return render_bash_card(state)
    elif name == "edit":
        return render_diff_card(state)
    elif name == "read":
        return render_file_read_card(state)
    elif name == "write":
        return render_file_write_card(state)
    elif name == "grep":
        return render_grep_card(state)
    elif name == "glob":
        return render_glob_card(state)
    elif name == "web_search":
        return render_web_search_card(state)
    elif name == "web_fetch":
        return render_web_fetch_card(state)
    else:
        return render_default_card(state)


__all__ = [
    "ToolCardState",
    "ToolState",
    "ThinkingDrawer",
    "render_tool_card",
    "render_bash_card",
    "render_diff_card",
    "render_file_read_card",
    "render_file_write_card",
    "render_grep_card",
    "render_glob_card",
    "render_web_search_card",
    "render_web_fetch_card",
    "render_default_card",
]
