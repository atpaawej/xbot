"""Unified git-style diff renderer for the file edit tool."""

from __future__ import annotations

import difflib
from typing import Optional

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from xbot.tui.cards.base import (
    ToolCardState,
    ToolState,
    clean_rel_path,
    truncate_tail,
)


def _generate_diff(
    filename: str, target_content: str, replacement_content: str
) -> tuple[str, int, int]:
    """Generate unified diff string and return (diff_text, added_lines_count, removed_lines_count)."""
    old_lines = target_content.splitlines(keepends=True)
    new_lines = replacement_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            n=3,
        )
    )

    if not diff_lines:
        return "", 0, 0

    added = 0
    removed = 0
    for line in diff_lines:
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    return "".join(diff_lines), added, removed


def render_diff_card(state: ToolCardState) -> Panel:
    """Render a unified, syntax-highlighted git diff card for file modifications."""
    raw_path = state.args.get("path") or "(unknown file)"
    display_path = clean_rel_path(raw_path)
    target_content = state.args.get("target_content", "")
    replacement_content = state.args.get("replacement_content", "")

    diff_text, added_count, removed_count = _generate_diff(
        display_path, target_content, replacement_content
    )

    # Header title
    title_text = Text()
    title_text.append("✏️ ", style="bold bright_cyan")
    title_text.append("edit: ", style="bold bright_white")
    title_text.append(display_path, style="bold cyan")

    # Status & stats pill
    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • ", style="yellow")
        status_pill.append("running", style="bold yellow")
        status_pill.append("]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (state.result and "Error:" in state.result):
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        stats = f"+{added_count}, -{removed_count}"
        status_pill.append(f" [✓ {stats} • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []

    # If diff was generated, render it with diff syntax highlighting
    if diff_text:
        tail_diff, omitted = truncate_tail(diff_text, max_lines=16)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} diff lines omitted ...]", style="dim italic"))
        content_items.append(
            Syntax(tail_diff, "diff", theme="monokai", word_wrap=True, line_numbers=False)
        )
    elif target_content or replacement_content:
        # Fallback if diff produced no changes
        change_desc = Text()
        change_desc.append("Replace target block with replacement content", style="dim italic")
        content_items.append(change_desc)

    # Error message preview if failed
    if state.result and ("Error:" in state.result or state.is_error):
        content_items.append(Text("─" * 40, style="red dim"))
        content_items.append(Text(f"❌ {state.result.strip()}", style="bold red"))

    return Panel(
        Group(*content_items) if content_items else Text("No content changed", style="dim"),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )
