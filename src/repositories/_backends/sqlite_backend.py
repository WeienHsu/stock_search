import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from src.core.repository_base import RepositoryBase

_DEFAULT_DB = Path(__file__).parents[3] / "data" / "users.db"


class SqliteBackend(RepositoryBase):
    """
    Stores user data as JSON values in a SQLite key-value table.
    Suitable for watchlist, preferences, risk_settings.
    Large binary objects (DataFrames) should still use PickleBackend.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or _DEFAULT_DB

    def _conn(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                user_id    TEXT NOT NULL,
                key        TEXT NOT NULL,
                value      TEXT NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY (user_id, key)
            )
        """)
        conn.commit()
        return conn

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM kv_store WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone()
        return json.loads(row[0]) if row else default

    def save(self, user_id: str, key: str, value: Any) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO kv_store (user_id, key, value, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, key, json.dumps(value, ensure_ascii=False), time.time()),
            )

    def delete(self, user_id: str, key: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM kv_store WHERE user_id = ? AND key = ?",
                (user_id, key),
            )

    def exists(self, user_id: str, key: str) -> bool:
        with self._conn() as conn:
            return conn.execute(
                "SELECT 1 FROM kv_store WHERE user_id = ? AND key = ?",
                (user_id, key),
            ).fetchone() is not None
