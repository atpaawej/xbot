"""Sessions management module for xbot."""

from xbot.sessions.database import get_connection, get_db_path
from xbot.sessions.manager import SessionManager, SessionSummary, generate_title

__all__ = [
    "SessionManager",
    "SessionSummary",
    "generate_title",
    "get_connection",
    "get_db_path",
]
