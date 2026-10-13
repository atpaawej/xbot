"""Base data structures, state models, and utilities for TUI tool cards."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from rich.text import Text


class ToolState(Enum):
    """Lifecycle state of an active tool invocation."""

    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ToolCardState:
    """State snapshot for a tool call card."""

    tool_name: str
    tool_call_id: str
    args: dict[str, Any] = field(default_factory=dict)
    state: ToolState = ToolState.RUNNING
    result: Optional[str] = None
    is_error: bool = False
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate elapsed or total execution duration in seconds."""
        end = self.end_time if self.end_time is not None else time.time()
        return max(0.0, end - self.start_time)

    @property
    def duration_str(self) -> str:
        """Human-readable duration string."""
        return f"{self.duration_seconds:.1f}s"


def format_status_badge(state: ToolState, is_error: bool = False) -> Text:
    """Render a colored status badge for tool headers."""
    if state == ToolState.RUNNING:
        badge = Text()
        badge.append("● ", style="bold yellow")
        badge.append("RUNNING", style="yellow")
        return badge
    if is_error or state == ToolState.ERROR:
        badge = Text()
        badge.append("❌ ", style="bold red")
        badge.append("FAILED", style="bold red")
        return badge
    badge = Text()
    badge.append("✓ ", style="bold green")
    badge.append("DONE", style="bold green")
    return badge


def truncate_tail(text: str, max_lines: int = 8) -> tuple[str, int]:
    """Keep the last `max_lines` of text. Returns (truncated_str, omitted_count)."""
    if not text:
        return "", 0
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text, 0
    omitted = len(lines) - max_lines
    retained = lines[-max_lines:]
    return "\n".join(retained), omitted


def truncate_head(text: str, max_lines: int = 8) -> tuple[str, int]:
    """Keep the first `max_lines` of text. Returns (truncated_str, omitted_count)."""
    if not text:
        return "", 0
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text, 0
    omitted = len(lines) - max_lines
    retained = lines[:max_lines]
    return "\n".join(retained), omitted


def clean_rel_path(raw_path: str) -> str:
    """Make paths relative to current working directory when possible for compact display."""
    if not raw_path:
        return ""
    try:
        p = Path(raw_path)
        cwd = Path.cwd()
        if p.is_absolute() and p.is_relative_to(cwd):
            return str(p.relative_to(cwd))
        return raw_path
    except Exception:
        return raw_path
