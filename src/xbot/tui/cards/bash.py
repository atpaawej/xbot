"""Bash tool card renderer with command prompt, cwd badge, duration, and output tailing."""

from __future__ import annotations

import re
from typing import Optional

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from xbot.config import get_config
from xbot.tui.cards.base import (
    ToolCardState,
    ToolState,
    clean_rel_path,
    truncate_tail,
)


def _extract_exit_code(result_text: Optional[str]) -> Optional[int]:
    """Parse returncode from bash tool output string."""
    if not result_text:
        return None
    match = re.search(r"Exit code:\s*(-?\d+)", result_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def render_bash_card(state: ToolCardState) -> Panel:
    """Render a unified, developer-friendly card for bash command executions."""
    command = state.args.get("command") or state.args.get("cmd") or "(no command)"
    action = state.args.get("action", "run")
    task_id = state.args.get("task_id", "")
    is_bg = state.args.get("is_bg", False)

    config = get_config()
    cwd_display = clean_rel_path(str(config.workspace_dir)) or "."

    # 1. Header elements
    title_text = Text()
    title_text.append("⚡ ", style="bold bright_yellow")
    title_text.append("bash", style="bold bright_white")

    if action != "run":
        title_text.append(f" ({action}", style="dim")
        if task_id:
            title_text.append(f" {task_id}", style="cyan")
        title_text.append(")", style="dim")

    # Status / exit pill
    status_pill = Text()
    exit_code = _extract_exit_code(state.result)

    if state.state == ToolState.RUNNING:
        status_pill.append(f" [⏱ {state.duration_str} • ", style="yellow")
        status_pill.append("running", style="bold yellow")
        status_pill.append("]", style="yellow")
        border_style = "bright_blue"
    elif state.is_error or (exit_code is not None and exit_code != 0):
        code_label = f"exit {exit_code}" if exit_code is not None else "failed"
        status_pill.append(f" [❌ {code_label} • {state.duration_str}]", style="bold red")
        border_style = "bold red"
    else:
        code_label = f"exit {exit_code}" if exit_code is not None else "done"
        status_pill.append(f" [✓ {code_label} • {state.duration_str}]", style="bold green")
        border_style = "green"

    title_text.append(status_pill)

    # 2. Command Prompt Line
    cmd_line = Text()
    cmd_line.append("$ ", style="bold bright_yellow")
    cmd_line.append(command, style="bold bright_white")
    if is_bg:
        cmd_line.append("  [background task]", style="dim magenta")

    content_items: list[RenderableType] = [cmd_line]

    # 3. Output Body (if completed)
    if state.result is not None:
        raw_result = state.result.strip()
        # Clean exit code header line from display if present to avoid duplication
        clean_lines = []
        for line in raw_result.splitlines():
            if line.startswith("Exit code:"):
                continue
            clean_lines.append(line)
        cleaned_body = "\n".join(clean_lines).strip()

        if cleaned_body:
            tail_body, omitted = truncate_tail(cleaned_body, max_lines=8)
            body_group = []
            if omitted > 0:
                body_group.append(Text(f"   [... {omitted} lines omitted ...]", style="dim italic"))
            body_group.append(Syntax(tail_body, "bash", theme="monokai", word_wrap=True))
            content_items.append(Text("─" * 40, style="dim"))
            content_items.extend(body_group)
        else:
            content_items.append(Text("   (no output)", style="dim italic"))

    subtitle = f"[dim]cwd: {cwd_display}[/dim]"

    return Panel(
        Group(*content_items),
        title=title_text,
        subtitle=subtitle,
        subtitle_align="right",
        box=box.ROUNDED,
        border_style=border_style,
        padding=(0, 1),
    )
