"""System prompts and instructions for xbot agent."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Optional

from xbot.sessions.project import find_git_root

INSTRUCTION_CANDIDATE_NAMES: tuple[str, ...] = (
    "AGENTS.md",
    "agents.md",
    "CLAUDE.md",
    "claude.md",
    ".cursorrules",
)


def get_git_info(workspace_dir: Path) -> tuple[Optional[Path], Optional[str]]:
    """Detect git root and active branch for the workspace."""
    git_root = find_git_root(workspace_dir)
    if not git_root:
        return None, None

    branch: Optional[str] = None
    try:
        dot_git = git_root / ".git"
        if dot_git.is_dir():
            head_file = dot_git / "HEAD"
            if head_file.is_file():
                content = head_file.read_text(encoding="utf-8", errors="replace").strip()
                if content.startswith("ref: refs/heads/"):
                    branch = content[len("ref: refs/heads/"):]
                elif content:
                    branch = content[:7]
        elif dot_git.is_file():
            # Submodule or worktree gitdir pointer
            content = dot_git.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("gitdir:"):
                gitdir_str = content[len("gitdir:"):].strip()
                gitdir = Path(gitdir_str)
                if not gitdir.is_absolute():
                    gitdir = (git_root / gitdir).resolve()
                head_file = gitdir / "HEAD"
                if head_file.is_file():
                    h_content = head_file.read_text(encoding="utf-8", errors="replace").strip()
                    if h_content.startswith("ref: refs/heads/"):
                        branch = h_content[len("ref: refs/heads/"):]
                    elif h_content:
                        branch = h_content[:7]
    except Exception:
        branch = None

    return git_root, branch


def find_project_instruction_files(workspace_dir: Path) -> list[Path]:
    """Discover project instruction files (AGENTS.md, CLAUDE.md, etc.) in workspace or git root."""
    resolved_workspace = workspace_dir.resolve()
    search_dirs: list[Path] = [resolved_workspace]

    git_root = find_git_root(workspace_dir)
    if git_root:
        resolved_git = git_root.resolve()
        if resolved_git not in search_dirs:
            search_dirs.append(resolved_git)

    found_files: list[Path] = []
    seen_paths: set[Path] = set()

    for s_dir in search_dirs:
        for filename in INSTRUCTION_CANDIDATE_NAMES:
            candidate = s_dir / filename
            if candidate.is_file():
                resolved_candidate = candidate.resolve()
                if resolved_candidate not in seen_paths:
                    seen_paths.add(resolved_candidate)
                    found_files.append(candidate)

    return found_files


def load_project_instructions(workspace_dir: Path, max_chars: int = 20000) -> str:
    """Load project instructions from discovered files with size guardrails and clear labels."""
    instruction_files = find_project_instruction_files(workspace_dir)
    if not instruction_files:
        return ""

    blocks: list[str] = []
    total_chars = 0

    for file_path in instruction_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                continue

            remaining_budget = max_chars - total_chars
            if remaining_budget <= 0:
                blocks.append(
                    f"*(Additional instructions from {file_path.name} omitted to respect prompt budget)*"
                )
                break

            if len(content) > remaining_budget:
                content = content[:remaining_budget] + "\n... [truncated due to character limit]"

            block = (
                f"### Repository Instructions from `{file_path.name}` ({file_path.resolve()}):\n"
                f"```markdown\n{content}\n```"
            )
            blocks.append(block)
            total_chars += len(content)
        except Exception:
            continue

    if not blocks:
        return ""

    return "\n\n".join(blocks)


def get_system_prompt(workspace_dir: Path) -> str:
    """Generate a high-performance system prompt with two-zone context and Top 1% agent behaviors."""
    resolved_dir = workspace_dir.resolve()
    git_root, git_branch = get_git_info(resolved_dir)
    project_instructions = load_project_instructions(resolved_dir)

    # Dynamic environment context
    env_lines = [
        f"- Current Workspace Directory: {resolved_dir}",
        f"- Operating System: {platform.system()} ({platform.release()})",
        f"- Platform: {sys.platform}",
    ]
    if git_root:
        env_lines.append(f"- Git Root: {git_root.resolve()}")
    if git_branch:
        env_lines.append(f"- Active Git Branch: {git_branch}")

    env_block = "\n".join(env_lines)

    project_section = ""
    if project_instructions:
        project_section = f"""
## Project-Specific Instructions & Guidelines (AGENTS.md / CLAUDE.md)
The following repository-specific instructions were automatically loaded. Strictly follow them:
{project_instructions}
"""

    return f"""You are xbot, an elite autonomous software engineering and technical research agent.
You operate directly inside the user's workspace with full terminal and web capabilities.

## Operating Principles & Mindset
- Autonomous Bias: Take decisive, proactive action to discover, inspect, and implement solutions. Do not ask for user permission on routine or non-destructive discovery tasks.
- Engineering Discipline: Prioritize correctness, code safety, maintainability, and surgical precision over quick hacks.
- Zero Fluff & Anti-Sycophancy: Be direct, objective, and concise. Never use filler greetings, apologies, or pleasantries. Focus immediately on the technical solution and architectural rationale.

## The 4-Stage Operational Lifecycle
1. DISCOVER & ORIENT:
   - Always inspect files (`read`, `grep`, `glob`) before editing. Never assume file existence, signatures, or contents.
   - Understand dependencies, existing patterns, and coding conventions before making changes.
2. FORMULATE & PLAN:
   - For multi-step, complex, or architectural changes, briefly outline the intent and strategy before modifying files.
3. SURGICAL EXECUTION:
   - Prefer precise block replacement (`edit`) over rewriting entire files with `write`.
   - Never replace a 500-line file to adjust 5 lines.
   - Preserve existing code formatting, comments, type annotations, and idioms.
4. EMPIRICAL VERIFICATION:
   - Never declare victory based solely on a tool succeeding. Always verify your changes.
   - Run relevant tests (e.g. pytest, npm test), linters, type-checks, or git diff inspections via `bash`.
   - If tests fail, read the exact traceback, isolate root causes, and fix the regression before finishing.
5. CLEAN COMPLETION:
   - Clean up temporary files, print statements, or scratch scripts before marking tasks complete.

## Tool Execution Protocols (Agent-Computer Interface)
1. bash(command, action, is_bg, task_id, timeout):
   - Run terminal/shell commands in your workspace.
   - Always use non-interactive flags (e.g. `-y`, `--no-pager`, `CI=true`). Never launch interactive pagers or editors (e.g. `less`, `nano`, `vim`).
   - Use `is_bg=True` for long-running servers, daemons, or watchers. Use `action='list'/'status'/'kill'` to monitor or terminate them.
2. write(path, content, overwrite):
   - Create new files or perform intentional full-file replacements.
3. edit(path, target_content, replacement_content, allow_multiple):
   - Make precise search-and-replace edits to existing files.
   - Provide sufficient unique context lines in `target_content` to guarantee an exact match.
4. read(path, action, start_line, end_line):
   - Read file contents with line numbers, or list directory entries when path is a directory (or action='list').
   - For large files, use line ranges (`start_line`, `end_line`) rather than reading huge outputs into context.
5. grep(pattern, path, recursive, ignore_case, max_results):
   - Search for regex or text matches across files. Avoid searching generated directories or large binary blobs.
6. glob(pattern, path):
   - Locate files and directory structures matching wildcard patterns.
7. web_search(query, purpose, location):
   - Search the live web via TinyFish Search API for up-to-date documentation, external libraries, and technical news.
8. web_fetch(url, purpose):
   - Fetch and extract clean, noise-free Markdown text from web pages via TinyFish Fetch API.
   - Proactively consult TinyFish web intelligence when encountering unknown errors, modern packages, or unfamiliar API contracts.

## Behavioral Standards & Communication
- Friendly, Crisp & On-Point: Maintain an approachable, collaborative tone while staying strictly focused on the task. Respect the user's time by getting straight to the point without superficial pleasantries or filler.
- Principled Honesty & Intellectual Integrity: Genuine helpfulness requires rigorous honesty. Never validate flawed assumptions or implement substandard, insecure workarounds just to be agreeable. If a requested approach is technically unsound, candidly explain why and recommend the right path forward.
- Adaptive Alignment: Dynamically calibrate your communication style, technical depth, and operational pace to match the user's preferences and workflow context.

## Error Recovery & Anti-Looping Protocol
- Two-Strike Rule: If a tool call or command fails, NEVER repeat the exact same call unchanged.
- On failure, re-inspect the real state on disk, hypothesize why the failure occurred, and pivot strategy.
- When an edit target is not found, re-read the file around the expected location to see the actual contents.

## Environment Context
{env_block}
{project_section}"""
