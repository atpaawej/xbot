"""SQLite database connection and schema management for centralized sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from xbot.config import get_config


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    """Resolve the SQLite database path.

    If custom_path is specified, uses that path directly (useful for tests).
    Otherwise, resolves to xbot.db inside the centralized data directory (~/.xbot).
    """
    if custom_path:
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path

    config = get_config()
    db_dir = config.ensure_data_dir()
    return db_dir / "xbot.db"


def get_connection(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create or connect to the SQLite database and ensure tables and migrations exist."""
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    with conn:
        conn.execute("PRAGMA foreign_keys = ON;")

        # Projects table for classifying sessions by workspace/repository
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                git_root TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        # Sessions table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model_id TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            );
            """
        )

        # Migration: Ensure project_id column exists if sessions table pre-existed
        cursor = conn.execute("PRAGMA table_info(sessions);")
        existing_cols = [row["name"] for row in cursor.fetchall()]
        if "project_id" not in existing_cols:
            conn.execute(
                "ALTER TABLE sessions ADD COLUMN project_id TEXT REFERENCES projects(id);"
            )

        # Session messages trace
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

        # Performance indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_project_id
            ON sessions (project_id);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_updated_at
            ON sessions (updated_at);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_session_messages_session_id
            ON session_messages (session_id);
            """
        )

    return conn
