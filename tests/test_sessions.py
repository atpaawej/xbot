"""Tests for SQLite sessions management."""

import pytest
from ai import user_message, assistant_message
from xbot.sessions import SessionManager, generate_title


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
