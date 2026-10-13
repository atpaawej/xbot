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
async def write(
    path: Optional[str] = None,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    contents: Optional[str] = None,
    text: Optional[str] = None,
    overwrite: bool = True,
) -> str:
    """Write or overwrite content to a file. Creates parent directories if they don't exist.

    Args:
        path: Relative or absolute path to the file (also accepts file_path).
        content: The text content to write (also accepts contents or text).
        file_path: Alternative parameter name for path.
        contents: Alternative parameter name for content.
        text: Alternative parameter name for content.
        overwrite: Whether to overwrite if the file already exists (default: True).

    Returns:
        Status message with file path, line count, and byte size.
    """
    target_path_str = path or file_path
    if not target_path_str:
        return "Error: File path is required. Please provide 'path' or 'file_path'."

    target_content = content if content is not None else (contents if contents is not None else text)
    if target_content is None:
        return f"Error: Content is required to write to '{target_path_str}'. Please provide 'content' or 'contents'."

    try:
        target = _resolve_path(target_path_str)
        if target.exists() and not overwrite:
            return f"Error: File '{target_path_str}' already exists and overwrite is set to False."

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(target_content, encoding="utf-8")

        line_count = len(target_content.splitlines())
        byte_size = len(target_content.encode("utf-8"))
        return f"Successfully wrote {line_count} lines ({byte_size} bytes) to '{target_path_str}'."
    except Exception as exc:
        return f"Error writing file '{target_path_str}': {exc}"


@tool
async def edit(
    path: Optional[str] = None,
    target_content: Optional[str] = None,
    replacement_content: Optional[str] = None,
    file_path: Optional[str] = None,
    old_string: Optional[str] = None,
    new_string: Optional[str] = None,
    allow_multiple: bool = False,
) -> str:
    """Replace an exact block of text in an existing file.

    Args:
        path: Path to the target file (also accepts file_path).
        target_content: The exact string block to replace (also accepts old_string).
        replacement_content: The new string block to insert in its place (also accepts new_string).
        file_path: Alternative parameter name for path.
        old_string: Alternative parameter name for target_content.
        new_string: Alternative parameter name for replacement_content.
        allow_multiple: If True, replaces all occurrences. If False, requires target to match exactly once.

    Returns:
        Status message describing the replacement outcome.
    """
    target_path_str = path or file_path
    if not target_path_str:
        return "Error: File path is required. Please provide 'path' or 'file_path'."

    target_str = target_content if target_content is not None else old_string
    if target_str is None:
        return f"Error: Target content to replace is required for '{target_path_str}'."

    replacement_str = replacement_content if replacement_content is not None else (new_string or "")

    try:
        target = _resolve_path(target_path_str)
        if not target.is_file():
            return f"Error: File '{target_path_str}' does not exist or is not a file."

        original = target.read_text(encoding="utf-8")

        count = original.count(target_str)
        if count == 0:
            return (
                f"Error: target_content not found in '{target_path_str}'. "
                "Please verify the exact text including whitespace and indentation."
            )

        if count > 1 and not allow_multiple:
            return (
                f"Error: target_content found {count} times in '{target_path_str}'. "
                "Provide more surrounding context lines to make it unique, or set allow_multiple=True."
            )

        if allow_multiple:
            modified = original.replace(target_str, replacement_str)
        else:
            modified = original.replace(target_str, replacement_str, 1)

        target.write_text(modified, encoding="utf-8")
        return f"Successfully replaced {count} occurrence(s) in '{target_path_str}'."
    except Exception as exc:
        return f"Error editing file '{target_path_str}': {exc}"


@tool
async def read(
    path: Optional[str] = None,
    file_path: Optional[str] = None,
    action: str = "read",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> str:
    """Read contents of a file with line numbers or list directory contents.

    Args:
        path: Relative or absolute path to the file or directory (also accepts file_path).
        file_path: Alternative parameter name for path.
        action: 'read' to read file contents, or 'list' (or 'ls') to list directory entries.
                If path points to a directory, it automatically lists its contents.
        start_line: Optional 1-indexed start line when reading files.
        end_line: Optional 1-indexed end line (inclusive) when reading files.

    Returns:
        Formatted file text with line numbers or formatted directory listing.
    """
    target_path_str = path or file_path or "."
    try:
        target = _resolve_path(target_path_str)
        if not target.exists():
            return f"Error: Path '{target_path_str}' does not exist."

        act = (action or "read").strip().lower()

        # Handle directory listing (either explicitly requested or target is a directory)
        if act in ("list", "ls") or target.is_dir():
            if not target.is_dir():
                return f"Error: Path '{target_path_str}' is a file, not a directory. Use action='read' to read its content."

            entries = list(target.iterdir())
            # Filter ignored dirs if listing root
            dirs = sorted([e for e in entries if e.is_dir() and e.name not in IGNORE_DIRS], key=lambda x: x.name)
            files = sorted([e for e in entries if e.is_file()], key=lambda x: x.name)

            lines = [f"--- Directory listing: {target_path_str} ({len(dirs)} dirs, {len(files)} files) ---"]
            for d in dirs:
                lines.append(f"  [DIR]  {d.name}/")
            for f in files:
                size = f.stat().st_size
                lines.append(f"  [FILE] {f.name:<30} ({size} bytes)")

            return "\n".join(lines)

        # File reading logic
        content = target.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        s = max(1, start_line) if start_line is not None else 1
        e = min(total_lines, end_line) if end_line is not None else total_lines

        if s > total_lines:
            return f"Error: start_line {s} exceeds total lines ({total_lines}) in '{target_path_str}'."

        selected = lines[s - 1 : e]
        formatted = [f"{s + idx:6d} | {line}" for idx, line in enumerate(selected)]

        header = f"--- {target_path_str} (lines {s}-{e} of {total_lines}) ---"
        return f"{header}\n" + "\n".join(formatted)
    except Exception as exc:
        return f"Error reading '{target_path_str}': {exc}"


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
