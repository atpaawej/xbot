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
from xbot.sessions.project import (
    ProjectSummary,
    resolve_project_identity,
)


@dataclass
class SessionSummary:
    id: str
    title: str
    created_at: str
    updated_at: str
    model_id: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None


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
    """Manages SQLite storage for conversation sessions and project classifications."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
    ) -> None:
        self.db_path = db_path
        self.workspace_dir = workspace_dir
        self.active_project: Optional[ProjectSummary] = None

        if self.workspace_dir is not None:
            self.active_project = self.get_or_create_project(self.workspace_dir)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_or_create_project(self, workspace_dir: Path) -> ProjectSummary:
        """Resolve and register a project from a workspace directory."""
        p_id, p_name, canon_path, git_root = resolve_project_identity(workspace_dir)
        canon_path_str = str(canon_path)
        git_root_str = str(git_root) if git_root is not None else None
        now = self._now()

        conn = get_connection(self.db_path)
        with conn:
            cursor = conn.execute(
                "SELECT id, name, path, git_root, created_at, updated_at FROM projects WHERE id = ?;",
                (p_id,),
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    "UPDATE projects SET updated_at = ? WHERE id = ?;",
                    (now, p_id),
                )
                summary = ProjectSummary(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    git_root=row["git_root"],
                    created_at=row["created_at"],
                    updated_at=now,
                )
            else:
                conn.execute(
                    """
                    INSERT INTO projects (id, name, path, git_root, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (p_id, p_name, canon_path_str, git_root_str, now, now),
                )
                summary = ProjectSummary(
                    id=p_id,
                    name=p_name,
                    path=canon_path_str,
                    git_root=git_root_str,
                    created_at=now,
                    updated_at=now,
                )

        self.active_project = summary
        return summary

    def list_projects(self) -> list[ProjectSummary]:
        """List all projects registered in the central database."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            """
            SELECT id, name, path, git_root, created_at, updated_at
            FROM projects
            ORDER BY updated_at DESC;
            """
        )
        rows = cursor.fetchall()
        return [
            ProjectSummary(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                git_root=row["git_root"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_project(self, project_id: str) -> Optional[ProjectSummary]:
        """Fetch project details by project ID."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            """
            SELECT id, name, path, git_root, created_at, updated_at
            FROM projects
            WHERE id = ?;
            """,
            (project_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ProjectSummary(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            git_root=row["git_root"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_session(
        self,
        first_prompt: Optional[str] = None,
        model_id: str = "gpt-4o",
        custom_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> SessionSummary:
        """Create a new session record in the database."""
        session_id = custom_id or uuid.uuid4().hex[:8]
        title = generate_title(first_prompt) if first_prompt else "New Session"
        now = self._now()

        p_id = project_id or (self.active_project.id if self.active_project else None)
        p_name = None
        if self.active_project and self.active_project.id == p_id:
            p_name = self.active_project.name

        conn = get_connection(self.db_path)
        with conn:
            conn.execute(
                """
                INSERT INTO sessions (id, project_id, title, created_at, updated_at, model_id)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (session_id, p_id, title, now, now, model_id),
            )

            # If project name not cached from active project, fetch from db
            if p_id and not p_name:
                row = conn.execute(
                    "SELECT name FROM projects WHERE id = ?;", (p_id,)
                ).fetchone()
                if row:
                    p_name = row["name"]

        return SessionSummary(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            model_id=model_id,
            project_id=p_id,
            project_name=p_name,
        )

    def get_session(self, session_id: str) -> Optional[SessionSummary]:
        """Fetch session metadata by session ID."""
        conn = get_connection(self.db_path)
        cursor = conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at, s.model_id, s.project_id, p.name AS project_name
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.id = ?;
            """,
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
            project_id=row["project_id"],
            project_name=row["project_name"],
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

    def list_sessions(
        self,
        project_id: Optional[str] = None,
        all_projects: bool = False,
        limit: int = 50,
    ) -> list[SessionSummary]:
        """List sessions ordered by most recently updated.

        By default, if all_projects is False and an active project exists,
        filters sessions belonging to the active project.
        """
        conn = get_connection(self.db_path)

        target_project_id = project_id or (
            self.active_project.id if (not all_projects and self.active_project) else None
        )

        if target_project_id and not all_projects:
            cursor = conn.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at, s.model_id, s.project_id, p.name AS project_name
                FROM sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                WHERE s.project_id = ?
                ORDER BY s.updated_at DESC
                LIMIT ?;
                """,
                (target_project_id, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at, s.model_id, s.project_id, p.name AS project_name
                FROM sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                ORDER BY s.updated_at DESC
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
                project_id=row["project_id"],
                project_name=row["project_name"],
            )
            for row in rows
        ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        conn = get_connection(self.db_path)
        with conn:
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?;", (session_id,))
            return cursor.rowcount > 0
