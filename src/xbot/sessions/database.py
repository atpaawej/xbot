"""SQLite database connection and schema management for sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from xbot.config import get_config


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the SQLite database path."""
    if custom_path:
        return custom_path
    config = get_config()
    db_dir = config.workspace_dir / ".xbot"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "sessions.db"


def get_connection(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create or connect to the SQLite database and ensure tables exist."""
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model_id TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_session_messages_session_id
            ON session_messages (session_id);
            """
        )

    return conn
