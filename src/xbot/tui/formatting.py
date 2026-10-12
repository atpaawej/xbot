"""Formatting helpers for Rich TUI."""

from __future__ import annotations

import json
from typing import Any

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text


def format_markdown(content: str) -> Markdown:
    """Render markdown string with pygments syntax highlighting."""
    return Markdown(content, code_theme="monokai", inline_code_lexer="text")


def format_json(data: Any) -> Syntax:
    """Format dictionary or JSON data with syntax highlighting."""
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            json_str = json.dumps(parsed, indent=2)
        except Exception:
            json_str = data
    else:
        json_str = json.dumps(data, indent=2, default=str)
    return Syntax(json_str, "json", theme="monokai", word_wrap=True)


def format_code_snippet(code: str, lexer: str = "python") -> Syntax:
    """Format a code snippet with line numbers and theme."""
    return Syntax(code, lexer, theme="monokai", line_numbers=True, word_wrap=True)


def truncate_preview(text: str, max_chars: int = 1200) -> str:
    """Truncate long text preview with notice."""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[... truncated {len(text) - max_chars} characters ...]"
