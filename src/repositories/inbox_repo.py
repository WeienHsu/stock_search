from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "alerts.db"


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inbox_messages (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            subject    TEXT NOT NULL,
            body       TEXT NOT NULL,
            severity   TEXT NOT NULL,
            read_at    REAL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inbox_user ON inbox_messages(user_id, created_at)")
    conn.commit()
    return conn


def add_message(
    user_id: str,
    subject: str,
    body: str,
    *,
    severity: str = "info",
    db_path: Path = _DEFAULT_DB,
) -> dict[str, Any]:
    message = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "subject": subject,
        "body": body,
        "severity": severity,
        "read_at": None,
        "created_at": time.time(),
    }
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO inbox_messages (id, user_id, subject, body, severity, read_at, created_at)
            VALUES (:id, :user_id, :subject, :body, :severity, :read_at, :created_at)
            """,
            message,
        )
    return message


def list_messages(
    user_id: str,
    *,
    unread_only: bool = False,
    limit: int = 50,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM inbox_messages WHERE user_id = ?"
    params: list[Any] = [user_id]
    if unread_only:
        query += " AND read_at IS NULL"
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(int(limit))
    with _conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def unread_count(user_id: str, *, db_path: Path = _DEFAULT_DB) -> int:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM inbox_messages WHERE user_id = ? AND read_at IS NULL",
            (user_id,),
        ).fetchone()
    return int(row[0])


def mark_read(message_id: str, *, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE inbox_messages SET read_at = ? WHERE id = ?",
            (time.time(), message_id),
        )
