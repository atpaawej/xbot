"""Unit tests for Git root detection and project identity resolution."""

from pathlib import Path
from xbot.sessions.project import (
    find_git_root,
    resolve_project_identity,
)
from xbot.sessions.manager import SessionManager


def test_find_git_root_in_repo():
    """Verify find_git_root finds repo root from deeply nested subdirectories."""
    current_dir = Path(__file__).resolve().parent
    git_root = find_git_root(current_dir)
    assert git_root is not None
    assert (git_root / ".git").exists()
    assert git_root == Path(__file__).resolve().parents[1]


def test_find_git_root_non_git(tmp_path):
    """Verify find_git_root returns None for directories outside git repos."""
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_git_root(nested) is None


def test_find_git_root_worktree_file(tmp_path):
    """Verify find_git_root supports .git as a file (git worktree / submodule)."""
    sub_repo = tmp_path / "subproject"
    sub_repo.mkdir()
    git_file = sub_repo / ".git"
    git_file.write_text("gitdir: ../.git/worktrees/subproject\n")

    sub_dir = sub_repo / "src" / "deep"
    sub_dir.mkdir(parents=True)

    assert find_git_root(sub_dir) == sub_repo


def test_resolve_project_identity_git():
    """Verify project identity resolves to the Git root even from a subfolder."""
    current_dir = Path(__file__).resolve().parent
    project_id, project_name, canonical_path, git_root = resolve_project_identity(current_dir)

    assert len(project_id) == 12
    assert git_root is not None
    assert canonical_path == git_root
    assert project_name == git_root.name


def test_resolve_project_identity_non_git(tmp_path):
    """Verify project identity uses resolved folder path when outside Git."""
    custom_dir = tmp_path / "standalone_app"
    custom_dir.mkdir()

    project_id, project_name, canonical_path, git_root = resolve_project_identity(custom_dir)
    assert len(project_id) == 12
    assert git_root is None
    assert canonical_path == custom_dir.resolve()
    assert project_name == "standalone_app"


def test_project_registration_and_listing(tmp_path):
    """Verify projects are stored and queryable in the central database."""
    db_file = tmp_path / "central.db"
    proj_dir_1 = tmp_path / "proj_alpha"
    proj_dir_1.mkdir()
    proj_dir_2 = tmp_path / "proj_beta"
    proj_dir_2.mkdir()

    manager = SessionManager(db_path=db_file, workspace_dir=proj_dir_1)
    assert manager.active_project is not None
    assert manager.active_project.name == "proj_alpha"

    # Register second project
    proj_2 = manager.get_or_create_project(proj_dir_2)
    assert proj_2.name == "proj_beta"

    projects = manager.list_projects()
    assert len(projects) == 2
    names = [p.name for p in projects]
    assert "proj_alpha" in names
    assert "proj_beta" in names
