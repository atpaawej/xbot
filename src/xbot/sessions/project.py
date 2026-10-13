"""Project identification and Git root detection for centralized session management."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProjectSummary:
    """Summary of a project registered in the central session database."""

    id: str
    name: str
    path: str
    git_root: Optional[str]
    created_at: str
    updated_at: str


def find_git_root(start_path: Path) -> Optional[Path]:
    """Walk up parent directories from start_path to find the enclosing Git root.

    Handles standard Git directories and Git submodules/worktrees (.git files).
    """
    current = start_path.resolve()
    for parent in [current, *current.parents]:
        git_marker = parent / ".git"
        if git_marker.exists():
            return parent
    return None


def resolve_project_identity(
    workspace_dir: Path,
) -> tuple[str, str, Path, Optional[Path]]:
    """Determine the canonical project identity for a workspace directory.

    Returns:
        tuple of (project_id, project_name, canonical_path, git_root)
        - project_id: A deterministic 12-character SHA256 hash of canonical_path.
        - project_name: The base directory name of the canonical path.
        - canonical_path: The Git root if found, else resolved workspace_dir.
        - git_root: The Git root path if within a Git repo, else None.
    """
    resolved_dir = workspace_dir.resolve()
    git_root = find_git_root(resolved_dir)
    canonical_path = git_root if git_root is not None else resolved_dir

    project_name = canonical_path.name or "root"
    project_id = hashlib.sha256(
        canonical_path.as_posix().encode("utf-8")
    ).hexdigest()[:12]

    return project_id, project_name, canonical_path, git_root
