"""Session manager for saving, loading, and listing agent conversation sessions."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ai.types.messages import Message
from xbot.sessions.database import get_connection


@dataclass
class SessionSummary:
    id: str
    title: str
    created_at: str
    updated_at: str
    model_id: str


def generate_title(prompt: str, max_chars: int = 42) -> str:
    """Generate a clean, user-readable title from the initial user prompt."""
    if not prompt:
        return "New Session"

    # Take first line and remove markdown/code/punctuation noise
    first_line = prompt.strip().splitlines()[0]
    cleaned = re.sub(r"[#*`_~\[\]()|]", "", first_line).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned:
        return "New Session"

    if len(cleaned) <= max_chars:
        return cleaned

    # Truncate at word boundary if possible
    truncated = cleaned[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > 15:
        truncated = truncated[:last_space]

    return f"{truncated}..."


class SessionManager:
    """Manages SQLite storage for conversation sessions."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_session(
        self,
        first_prompt: Optional[str] = None,
        model_id: str = "gpt-4o",
        custom_id: Optional[str] = None,
    ) -> SessionSummary:
        """Create a new session record in the database."""
        session_id = custom_id or uuid.uuid4().hex[:8]
        title = generate_title(first_prompt) if first_prompt else "New Session"
        now = self._now()

        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, created_at, updated_at, model_id)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_id, title, now, now, model_id),
            )

        return SessionSummary(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            model_id=model_id,
        )

    def get_session(self, session_id: str) -> Optional[SessionSummary]:
        """Fetch session metadata by session ID."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            "SELECT id, title, created_at, updated_at, model_id FROM sessions WHERE id = ?;",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SessionSummary(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            model_id=row["model_id"],
        )

    def update_title(self, session_id: str, new_title: str) -> None:
        """Update the human-readable title of a session."""
        now = self._now()
        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?;",
                (new_title, now, session_id),
            )

    def save_messages(self, session_id: str, messages: list[Message]) -> None:
        """Persist serialized messages for a session."""
        now = self._now()
        conn = get_connection(self.db_path)
        with conn:
            # Clear previous messages to store the full consistent trace
            conn.execute(
                "DELETE FROM session_messages WHERE session_id = ?;",
                (session_id,),
            )

            # Insert all messages
            for msg in messages:
                role = getattr(msg, "role", "unknown")
                data_dict = msg.model_dump()
                data_json = json.dumps(data_dict, default=str)
                conn.execute(
                    """
                    INSERT INTO session_messages (session_id, role, data_json, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (session_id, role, data_json, now),
                )

            # Update session timestamp
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?;",
                (now, session_id),
            )

    def load_messages(self, session_id: str) -> list[Message]:
        """Load and reconstruct Message instances for a session."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            "SELECT role, data_json FROM session_messages WHERE session_id = ? ORDER BY id ASC;",
            (session_id,),
        )
        rows = cursor.fetchall()

        reconstructed: list[Message] = []
        for row in rows:
            try:
                data = json.loads(row["data_json"])
                msg = Message.model_validate(data)
                reconstructed.append(msg)
            except Exception:
                pass

        return reconstructed

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        """List sessions ordered by most recently updated."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            """
            SELECT id, title, created_at, updated_at, model_id
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            SessionSummary(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                model_id=row["model_id"],
            )
            for row in rows
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        conn = get_connection(self.db_path)
        with conn:
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
            return cursor.rowcount > 0
