"""Sessions management module for xbot."""

from xbot.sessions.database import get_connection, get_db_path
from xbot.sessions.manager import SessionManager, SessionSummary, generate_title
from xbot.sessions.project import (
    ProjectSummary,
    find_git_root,
    resolve_project_identity,
)

__all__ = [
    "ProjectSummary",
    "SessionManager",
    "SessionSummary",
    "find_git_root",
    "generate_title",
    "get_connection",
    "get_db_path",
    "resolve_project_identity",
]
