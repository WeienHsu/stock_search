from typing import Any
import json
import time

from src.core.repository_base import RepositoryBase
from src.core.database import get_connection


class PostgresBackend(RepositoryBase):
    """
    Stores user data as JSON values in a PostgreSQL key-value table.
    Suitable for watchlist, preferences, risk_settings.
    """

    def _conn(self):
        conn = get_connection("users")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                user_id    VARCHAR(255) NOT NULL,
                key        VARCHAR(255) NOT NULL,
                value      TEXT NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (user_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id    VARCHAR(255) NOT NULL,
                namespace  VARCHAR(255) NOT NULL,
                payload    TEXT NOT NULL,
                updated_at DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (user_id, namespace)
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

    def purge_user(self, user_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM kv_store WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))

    def get_user_preference(self, user_id: str, namespace: str, default: Any = None) -> Any:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM user_preferences WHERE user_id = ? AND namespace = ?",
                (user_id, namespace),
            ).fetchone()
        return json.loads(row[0]) if row else default

    def set_user_preference(self, user_id: str, namespace: str, payload: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO user_preferences (user_id, namespace, payload, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, namespace, json.dumps(payload, ensure_ascii=False), time.time()),
            )

    def patch_user_preference(self, user_id: str, namespace: str, partial: dict[str, Any]) -> dict[str, Any]:
        payload = self.get_user_preference(user_id, namespace, default={}) or {}
        payload = {**payload, **partial}
        self.set_user_preference(user_id, namespace, payload)
        return payload
