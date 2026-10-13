"""Tests for SQLite sessions management with project classification."""

import sqlite3
import pytest
from pathlib import Path
from ai import user_message, assistant_message
from xbot.config import Config, set_config
from xbot.sessions import (
    SessionManager,
    generate_title,
    get_connection,
    get_db_path,
)


def test_generate_title():
    """Test title generation from various prompt formats."""
    assert generate_title("Hello world") == "Hello world"
    assert generate_title("### Setup Python AI Agent with Rich") == "Setup Python AI Agent with Rich"
    assert generate_title("") == "New Session"
    long_prompt = "Can you please help me build an automated financial portfolio tracker using SQLite and Python?"
    title = generate_title(long_prompt)
    assert len(title) <= 45
    assert title.endswith("...")


def test_session_lifecycle(tmp_path):
    """Test creating, saving messages, loading messages, and listing sessions."""
    db_file = tmp_path / "test_sessions.db"
    manager = SessionManager(db_path=db_file)

    # Create session
    session = manager.create_session(first_prompt="Help me write tests", model_id="gpt-4o")
    assert session.id is not None
    assert session.title == "Help me write tests"
    assert session.model_id == "gpt-4o"

    # Save messages
    msgs = [
        user_message("Help me write tests"),
        assistant_message("Sure, here are tests."),
    ]
    manager.save_messages(session.id, msgs)

    # Load messages
    loaded = manager.load_messages(session.id)
    assert len(loaded) == 2
    assert loaded[0].role == "user"
    assert loaded[1].role == "assistant"

    # List sessions
    summaries = manager.list_sessions()
    assert len(summaries) == 1
    assert summaries[0].id == session.id
    assert summaries[0].title == session.title

    # Delete session
    assert manager.delete_session(session.id) is True
    assert len(manager.list_sessions()) == 0


def test_project_filtered_sessions(tmp_path):
    """Test session association with projects and filtering in list_sessions."""
    db_file = tmp_path / "projects_test.db"
    dir_a = tmp_path / "project_a"
    dir_a.mkdir()
    dir_b = tmp_path / "project_b"
    dir_b.mkdir()

    mgr_a = SessionManager(db_path=db_file, workspace_dir=dir_a)
    mgr_b = SessionManager(db_path=db_file, workspace_dir=dir_b)

    # Create sessions in project A
    sess_a1 = mgr_a.create_session(first_prompt="Task in Project A")
    assert sess_a1.project_id == mgr_a.active_project.id
    assert sess_a1.project_name == "project_a"

    # Create session in project B
    sess_b1 = mgr_b.create_session(first_prompt="Task in Project B")
    assert sess_b1.project_id == mgr_b.active_project.id
    assert sess_b1.project_name == "project_b"

    # Project A manager should only list project A's sessions by default
    sessions_for_a = mgr_a.list_sessions(all_projects=False)
    assert len(sessions_for_a) == 1
    assert sessions_for_a[0].id == sess_a1.id

    # Project B manager should only list project B's sessions by default
    sessions_for_b = mgr_b.list_sessions(all_projects=False)
    assert len(sessions_for_b) == 1
    assert sessions_for_b[0].id == sess_b1.id

    # all_projects=True returns both sessions
    all_sessions = mgr_a.list_sessions(all_projects=True)
    assert len(all_sessions) == 2


def test_database_migration_from_legacy_schema(tmp_path):
    """Verify that a legacy database lacking project_id is smoothly migrated."""
    db_file = tmp_path / "legacy.db"

    # Create old schema directly without project_id or projects table
    raw_conn = sqlite3.connect(str(db_file))
    with raw_conn:
        raw_conn.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                model_id TEXT NOT NULL
            );
            """
        )
        raw_conn.execute(
            """
            INSERT INTO sessions VALUES ('legacy_s1', 'Legacy Session', '2026-01-01', '2026-01-01', 'gpt-4o');
            """
        )
    raw_conn.close()

    # Now open with get_connection to run automatic migrations
    conn = get_connection(custom_path=db_file)
    cursor = conn.execute("PRAGMA table_info(sessions);")
    col_names = [r["name"] for r in cursor.fetchall()]
    assert "project_id" in col_names

    # Manager should load legacy session without issue
    manager = SessionManager(db_path=db_file)
    session = manager.get_session("legacy_s1")
    assert session is not None
    assert session.title == "Legacy Session"
    assert session.project_id is None
    assert session.project_name is None


def test_centralized_default_db_path(tmp_path, monkeypatch):
    """Verify that default database resolves to ~/.xbot or XBOT_DATA_DIR without touching workspace."""
    custom_data = tmp_path / "my_global_data"
    monkeypatch.setenv("XBOT_DATA_DIR", str(custom_data))

    cfg = Config.load()
    set_config(cfg)

    db_path = get_db_path()
    assert db_path == custom_data / "xbot.db"
    assert not (cfg.workspace_dir / ".xbot").exists()
