"""File operation tools: write, edit, read, grep, glob."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from ai import tool
from xbot.config import get_config

# Ignored directories for grep and glob
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
}


def _resolve_path(path_str: str) -> Path:
    """Resolve a path against workspace directory."""
    config = get_config()
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (config.workspace_dir / p).resolve()


@tool
async def write(path: str, content: str, overwrite: bool = True) -> str:
    """Write or overwrite content to a file. Creates parent directories if they don't exist.

    Args:
        path: Relative or absolute path to the file.
        content: The text content to write.
        overwrite: Whether to overwrite if the file already exists (default: True).

    Returns:
        Status message with file path, line count, and byte size.
    """
    try:
        target = _resolve_path(path)
        if target.exists() and not overwrite:
            return f"Error: File '{path}' already exists and overwrite is set to False."

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        line_count = len(content.splitlines())
        byte_size = len(content.encode("utf-8"))
        return f"Successfully wrote {line_count} lines ({byte_size} bytes) to '{path}'."
    except Exception as exc:
        return f"Error writing file '{path}': {exc}"


@tool
async def edit(
    path: str,
    target_content: str,
    replacement_content: str,
    allow_multiple: bool = False,
) -> str:
    """Replace an exact block of text in an existing file.

    Args:
        path: Path to the target file.
        target_content: The exact string block to replace.
        replacement_content: The new string block to insert in its place.
        allow_multiple: If True, replaces all occurrences. If False, requires target to match exactly once.

    Returns:
        Status message describing the replacement outcome.
    """
    try:
        target = _resolve_path(path)
        if not target.is_file():
            return f"Error: File '{path}' does not exist or is not a file."

        original = target.read_text(encoding="utf-8")

        count = original.count(target_content)
        if count == 0:
            return (
                f"Error: target_content not found in '{path}'. "
                "Please verify the exact text including whitespace and indentation."
            )

        if count > 1 and not allow_multiple:
            return (
                f"Error: target_content found {count} times in '{path}'. "
                "Provide more surrounding context lines to make it unique, or set allow_multiple=True."
            )

        if allow_multiple:
            modified = original.replace(target_content, replacement_content)
        else:
            modified = original.replace(target_content, replacement_content, 1)

        target.write_text(modified, encoding="utf-8")
        return f"Successfully replaced {count} occurrence(s) in '{path}'."
    except Exception as exc:
        return f"Error editing file '{path}': {exc}"


@tool
async def read(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> str:
    """Read contents of a file with line numbers.

    Args:
        path: Relative or absolute path to the file.
        start_line: Optional 1-indexed start line.
        end_line: Optional 1-indexed end line (inclusive).

    Returns:
        File contents formatted with line numbers, or an error message.
    """
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: Path '{path}' is a directory, not a file."

        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        s = max(1, start_line) if start_line is not None else 1
        e = min(total_lines, end_line) if end_line is not None else total_lines

        if s > total_lines:
            return f"Error: start_line {s} exceeds total lines ({total_lines}) in '{path}'."

        selected = lines[s - 1 : e]
        formatted = [f"{s + idx:6d} | {line}" for idx, line in enumerate(selected)]

        header = f"--- {path} (lines {s}-{e} of {total_lines}) ---"
        return f"{header}\n" + "\n".join(formatted)
    except Exception as exc:
        return f"Error reading file '{path}': {exc}"


@tool
async def grep(
    pattern: str,
    path: str = ".",
    recursive: bool = True,
    ignore_case: bool = False,
    max_results: int = 100,
) -> str:
    """Search for a regex or string pattern across files.

    Args:
        pattern: The regular expression or string pattern to search for.
        path: Directory or file to search within (default: current workspace).
        recursive: Whether to search subdirectories recursively (default: True).
        ignore_case: Whether to ignore casing (default: False).
        max_results: Maximum number of matching lines to return (default: 100).

    Returns:
        Formatted list of matching lines with file paths and line numbers.
    """
    try:
        target = _resolve_path(path)
        if not target.exists():
            return f"Error: Path '{path}' does not exist."

        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        matches: list[str] = []

        def search_file(f: Path) -> None:
            nonlocal matches
            if len(matches) >= max_results:
                return
            try:
                # Quick binary check
                with open(f, "rb") as check_bin:
                    chunk = check_bin.read(1024)
                    if b"\x00" in chunk:
                        return  # Skip binary file

                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
                for line_idx, line in enumerate(lines, start=1):
                    if regex.search(line):
                        rel_path = os.path.relpath(f, get_config().workspace_dir)
                        matches.append(f"{rel_path}:{line_idx}: {line.strip()}")
                        if len(matches) >= max_results:
                            return
            except Exception:
                pass

        if target.is_file():
            search_file(target)
        else:
            for root, dirs, files in os.walk(target):
                # Prune ignored directories in-place
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
                for file_name in files:
                    if len(matches) >= max_results:
                        break
                    file_path = Path(root) / file_name
                    search_file(file_path)
                if not recursive or len(matches) >= max_results:
                    break

        if not matches:
            return f"No matches found for pattern '{pattern}' in '{path}'."

        result_header = f"Found {len(matches)} match(es) for pattern '{pattern}':\n"
        return result_header + "\n".join(matches)
    except Exception as exc:
        return f"Error running grep for pattern '{pattern}': {exc}"


@tool
async def glob(pattern: str, path: str = ".") -> str:
    """Find files and directories matching a glob pattern (e.g. '**/*.py', 'src/*.ts').

    Args:
        pattern: Wildcard / glob pattern to match.
        path: Base directory to search from (default: current workspace).

    Returns:
        Sorted list of matching relative file paths.
    """
    try:
        base = _resolve_path(path)
        if not base.exists() or not base.is_dir():
            return f"Error: Path '{path}' does not exist or is not a directory."

        matches: list[str] = []
        for p in base.glob(pattern):
            # Check if any parent component is in ignored list
            parts = p.parts
            if any(part in IGNORE_DIRS or (part.startswith(".") and part != ".") for part in parts):
                continue
            rel = os.path.relpath(p, get_config().workspace_dir)
            matches.append(rel)

        matches.sort()
        if not matches:
            return f"No files matched glob pattern '{pattern}' under '{path}'."

        return f"Matched {len(matches)} item(s):\n" + "\n".join(matches[:200])
    except Exception as exc:
        return f"Error running glob for pattern '{pattern}': {exc}"
