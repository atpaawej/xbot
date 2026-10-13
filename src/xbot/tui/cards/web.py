"""TinyFish web intelligence card renderers for web_search and web_fetch."""

from __future__ import annotations

import re
from typing import Optional

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from xbot.tui.cards.base import ToolCardState, ToolState, truncate_tail


def render_web_search_card(state: ToolCardState) -> Panel:
    """Render structured web search card with query, domains, and snippet previews."""
    query = state.args.get("query", "")
    purpose = state.args.get("purpose")

    title_text = Text()
    title_text.append("🌐 ", style="bold bright_cyan")
    title_text.append("search: ", style="bold bright_white")
    title_text.append(f'"{query}"', style="bold bright_cyan")

    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • running]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (state.result and "Error:" in state.result):
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        # Approximate result count from "Total results:" or numbered items
        result_count_match = re.search(r"Total results:\s*(\d+)", state.result or "")
        count_str = (
            f"{result_count_match.group(1)} results"
            if result_count_match
            else "completed"
        )
        status_pill.append(f" [✓ {count_str} • {state.duration_str}]", style="bold green")
        border_style = "cyan"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []

    if purpose:
        content_items.append(Text(f"🎯 Intent: {purpose}", style="dim italic"))

    if state.result:
        clean_res = state.result.strip()
        # Find domains mentioned in results (e.g. URLs)
        domains = set(re.findall(r"https?://(?:www\.)?([^/\s]+)", clean_res))
        if domains:
            domain_chips = Text()
            domain_chips.append("Sources: ", style="dim")
            for d in list(domains)[:4]:
                domain_chips.append(f"[{d}] ", style="bold cyan")
            content_items.append(domain_chips)
            content_items.append(Text("─" * 40, style="dim"))

        tail_body, omitted = truncate_tail(clean_res, max_lines=6)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} lines omitted ...]", style="dim italic"))
        content_items.append(Text(tail_body, style="bright_white"))

    return Panel(
        Group(*content_items) if content_items else Text("Searching live web via TinyFish...", style="dim"),
        title=title_text,
        subtitle="[dim]TinyFish Web Intelligence[/dim]",
        subtitle_align="right",
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )


def render_web_fetch_card(state: ToolCardState) -> Panel:
    """Render web page fetch card with URL and extraction preview."""
    url = state.args.get("url", "")
    goal = state.args.get("goal")

    title_text = Text()
    title_text.append("🌐 ", style="bold bright_blue")
    title_text.append("fetch: ", style="bold bright_white")
    # Truncate long URLs in header
    short_url = url if len(url) <= 45 else f"{url[:42]}..."
    title_text.append(short_url, style="bold cyan")

    status_pill = Text()
    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • running]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (state.result and "Error:" in state.result):
        status_pill.append(f" [❌ failed • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        char_count = len(state.result) if state.result else 0
        status_pill.append(f" [✓ {char_count:,} chars • {state.duration_str}]", style="bold green")
        border_style = "cyan"

    title_text.append(status_pill)

    content_items: list[RenderableType] = []

    if goal:
        content_items.append(Text(f"🎯 Extraction Goal: {goal}", style="dim italic"))

    if state.result:
        clean_res = state.result.strip()
        tail_body, omitted = truncate_tail(clean_res, max_lines=5)
        if omitted > 0:
            content_items.append(Text(f"[... {omitted} lines omitted ...]", style="dim italic"))
        content_items.append(Text(tail_body, style="bright_white"))

    return Panel(
        Group(*content_items) if content_items else Text("Extracting markdown via TinyFish...", style="dim"),
        title=title_text,
        subtitle="[dim]TinyFish Web Fetch[/dim]",
        subtitle_align="right",
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )
