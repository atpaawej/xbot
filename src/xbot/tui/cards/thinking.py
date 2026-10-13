"""Model reasoning / chain-of-thought renderer with live timer and collapsed summary."""

from __future__ import annotations

import time
from typing import Optional

from rich import box
from rich.panel import Panel
from rich.text import Text


class ThinkingDrawer:
    """Manages reasoning delta accumulation, stopwatch timing, and rendering."""

    def __init__(self) -> None:
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.accumulated_text: str = ""
        self._is_finalized: bool = False

    def append(self, chunk: str) -> None:
        """Append streamed reasoning delta chunk."""
        if not self._is_finalized:
            self.accumulated_text += chunk

    def finalize(self) -> None:
        """Mark reasoning complete and freeze elapsed duration."""
        if not self._is_finalized:
            self.end_time = time.time()
            self._is_finalized = True

    @property
    def duration_seconds(self) -> float:
        """Elapsed time in seconds."""
        end = self.end_time if self.end_time is not None else time.time()
        return max(0.0, end - self.start_time)

    @property
    def duration_str(self) -> str:
        return f"{self.duration_seconds:.1f}s"

    def summary_preview(self, max_chars: int = 80) -> str:
        """Extract a single clean preview line from the accumulated reasoning."""
        cleaned = " ".join(self.accumulated_text.split()).strip()
        if not cleaned:
            return "Analyzed request"
        if len(cleaned) <= max_chars:
            return cleaned
        return f"{cleaned[:max_chars - 3]}..."

    def render_live(self) -> Panel:
        """Render active live thinking card with running timer and smooth rolling preview."""
        title_text = Text()
        title_text.append("💭 ", style="bold bright_magenta")
        title_text.append("Thinking... ", style="bold magenta")
        title_text.append(f"[⏱ {self.duration_str}]", style="bold yellow")

        # Take the last ~2 lines for rolling preview
        lines = [line.strip() for line in self.accumulated_text.splitlines() if line.strip()]
        preview_text = lines[-1] if lines else "Reasoning about solution..."
        if len(preview_text) > 120:
            preview_text = f"...{preview_text[-117:]}"

        content = Text(preview_text, style="italic dim magenta")

        return Panel(
            content,
            title=title_text,
            box=box.ROUNDED,
            border_style="magenta",
            padding=(0, 1),
        )

    def render_collapsed(self) -> Text:
        """Render completed thinking pill to leave a clean, non-intrusive trace."""
        pill = Text()
        pill.append("💭 Thought for ", style="dim magenta")
        pill.append(self.duration_str, style="bold magenta")
        pill.append(" • ", style="dim")
        pill.append(self.summary_preview(70), style="dim italic")
        return pill
