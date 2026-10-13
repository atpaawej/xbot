"""File operation card renderers for read, write, grep, and glob."""

from __future__ import annotations

import re
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
    truncate_head,
    truncate_tail,
)


def render_file_read_card(state: ToolCardState) -> Panel:
    """Render anti-clutter breadcrumb card for file reading operations."""
    raw_path = state.args.get("path") or "(unknown file)"
    display_path = clean_rel_path(raw_path)
    start_line = state.args.get("start_line")
    end_line = state.args.get("end_line")

    range_label = ""
    if start_line is not None and end_line is not None:
        range_label = f"lines {start_line}–{end_line}"
    elif start_line is not None:
        range_label = f"from line {start_line}"
    elif end_line is not None:
        range_label = f"up to line {end_line}"
    else:
        range_label = "entire file"

    # Header title
    title_text = Text()
    title_text.append("📖 ", style="bold bright_cyan")
    title_text.append("read: ", style="bold bright_white")
    title_text.append(display_path, style="bold cyan")

    # Status pill
    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [{range_label} • ⏱ {state.duration_str} • ", style="yellow")
        status_pill.append("running", style="bold yellow")
        status_pill.append("]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (state.result and "Error:" in state.result):
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        # Count lines read from result
        line_count = len(state.result.splitlines()) if state.result else 0
        status_pill.append(f" [✓ {range_label} • {line_count} lines • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []

    # If error occurred, show the error message in the body
    if state.result and ("Error:" in state.result or state.is_error):
        content_items.append(Text(f"❌ {state.result.strip()}", style="bold red"))
    else:
        # Sleek 1-line confirmation (does not dump full file to terminal)
        summary = Text()
        summary.append("  Content loaded into agent context ", style="dim italic")
        summary.append(f"({display_path})", style="dim cyan")
        content_items.append(summary)

    return Panel(
        Group(*content_items),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )


def render_file_write_card(state: ToolCardState) -> Panel:
    """Render file write card showing line counts, byte sizes, and preview."""
    raw_path = state.args.get("path") or "(unknown file)"
    display_path = clean_rel_path(raw_path)
    content = state.args.get("content", "")
    overwrite = state.args.get("overwrite", True)

    line_count = len(content.splitlines()) if content else 0
    byte_size = len(content.encode("utf-8")) if content else 0

    title_text = Text()
    title_text.append("📄 ", style="bold bright_blue")
    title_text.append("write: ", style="bold bright_white")
    title_text.append(display_path, style="bold cyan")

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
        status_pill.append(
            f" [✓ {line_count} lines, {byte_size}B • {state.duration_str}]",
            style="bold green",
        )
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []

    if state.result and ("Error:" in state.result or state.is_error):
        content_items.append(Text(f"❌ {state.result.strip()}", style="bold red"))
    elif content:
        # Preview first 5 lines
        head_preview, omitted = truncate_head(content, max_lines=5)
        # Determine lexer from extension
        ext = raw_path.rsplit(".", 1)[-1] if "." in raw_path else "text"
        content_items.append(
            Syntax(head_preview, ext, theme="monokai", line_numbers=True, word_wrap=True)
        )
        if omitted > 0:
            content_items.append(Text(f"   [... {omitted} more lines written ...]", style="dim italic"))

    return Panel(
        Group(*content_items),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )


def render_grep_card(state: ToolCardState) -> Panel:
    """Render grep search card with pattern and hit count."""
    pattern = state.args.get("pattern", "")
    search_path = clean_rel_path(state.args.get("path") or ".")

    title_text = Text()
    title_text.append("🔍 ", style="bold bright_yellow")
    title_text.append("grep: ", style="bold bright_white")
    title_text.append(f'"{pattern}"', style="bold yellow")
    title_text.append(f" in {search_path}", style="dim")

    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • running]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (state.result and "Error:" in state.result):
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        # Count matches
        match_count = (
            len(state.result.splitlines())
            if state.result and "No matches" not in state.result
            else 0
        )
        status_pill.append(f" [✓ {match_count} matches • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []
    if state.result:
        clean_res = state.result.strip()
        tail_body, omitted = truncate_tail(clean_res, max_lines=6)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} match lines omitted ...]", style="dim italic"))
        content_items.append(Text(tail_body, style="bright_white"))

    return Panel(
        Group(*content_items) if content_items else Text("Searching...", style="dim"),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )


def render_glob_card(state: ToolCardState) -> Panel:
    """Render glob pattern search card."""
    pattern = state.args.get("pattern", "")
    search_path = clean_rel_path(state.args.get("path") or ".")

    title_text = Text()
    title_text.append("📁 ", style="bold bright_yellow")
    title_text.append("glob: ", style="bold bright_white")
    title_text.append(f'"{pattern}"', style="bold yellow")
    title_text.append(f" in {search_path}", style="dim")

    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • running]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error:
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        file_count = (
            len(state.result.splitlines())
            if state.result and "No files found" not in state.result
            else 0
        )
        status_pill.append(f" [✓ {file_count} files • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []
    if state.result:
        clean_res = state.result.strip()
        tail_body, omitted = truncate_tail(clean_res, max_lines=6)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} files omitted ...]", style="dim italic"))
        content_items.append(Text(tail_body, style="bright_white"))

    return Panel(
        Group(*content_items) if content_items else Text("Scanning files...", style="dim"),
        title=title_text,
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )
