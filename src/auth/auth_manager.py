import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

import bcrypt

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "auth.db"


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    # Create users table (is_admin included for fresh DBs)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    TEXT PRIMARY KEY,
            username   TEXT UNIQUE NOT NULL,
            pw_hash    TEXT NOT NULL,
            created_at REAL NOT NULL,
            is_admin   INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Migration: add is_admin column to existing DBs that predate this schema
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "is_admin" not in existing_cols:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        # Auto-promote the earliest registered user if no admin exists yet
        conn.execute("""
            UPDATE users SET is_admin = 1
            WHERE user_id = (SELECT user_id FROM users ORDER BY created_at ASC LIMIT 1)
              AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = 1)
        """)

    # App-wide settings (registration toggle, etc.)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


def _is_registration_enabled_conn(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = 'registration_enabled'"
    ).fetchone()
    return row is None or row[0] == "1"


# ── Public auth API ──

def register_user(
    username: str,
    password: str,
    db_path: Path = _DEFAULT_DB,
) -> str:
    """Create a new user. Returns user_id. Raises ValueError on validation failure."""
    if len(password) < 6:
        raise ValueError("密碼至少需要 6 個字元")

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())

    with _conn(db_path) as conn:
        is_first = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is None
        if not is_first and not _is_registration_enabled_conn(conn):
            raise ValueError("註冊已停用，請聯絡管理員")
        try:
            conn.execute(
                "INSERT INTO users (user_id, username, pw_hash, created_at, is_admin) VALUES (?,?,?,?,?)",
                (user_id, username.strip(), pw_hash, time.time(), 1 if is_first else 0),
            )
        except sqlite3.IntegrityError:
            raise ValueError("用戶名已存在")

    return user_id


def authenticate(
    username: str,
    password: str,
    db_path: Path = _DEFAULT_DB,
) -> Optional[dict]:
    """Return dict(user_id, is_admin) if credentials are valid, else None."""
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT user_id, pw_hash, is_admin FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        return {"user_id": row[0], "is_admin": bool(row[2])}
    return None


def user_exists(db_path: Path = _DEFAULT_DB) -> bool:
    """Return True if at least one user account exists."""
    with _conn(db_path) as conn:
        return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None


# ── Registration control ──

def is_registration_enabled(db_path: Path = _DEFAULT_DB) -> bool:
    with _conn(db_path) as conn:
        return _is_registration_enabled_conn(conn)


def set_registration_enabled(enabled: bool, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('registration_enabled', ?)",
            ("1" if enabled else "0",),
        )


# ── Admin / user management ──

def list_users(db_path: Path = _DEFAULT_DB) -> list[dict]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT user_id, username, created_at, is_admin FROM users ORDER BY created_at ASC"
        ).fetchall()
    return [
        {"user_id": r[0], "username": r[1], "created_at": r[2], "is_admin": bool(r[3])}
        for r in rows
    ]


def delete_user(user_id: str, db_path: Path = _DEFAULT_DB) -> None:
    """Remove user from auth DB. Caller should purge kv_store data separately."""
    with _conn(db_path) as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def set_admin(user_id: str, is_admin: bool, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if is_admin else 0, user_id),
        )


def is_user_admin(user_id: str, db_path: Path = _DEFAULT_DB) -> bool:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT is_admin FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return bool(row and row[0])
