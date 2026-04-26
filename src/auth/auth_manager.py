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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   TEXT PRIMARY KEY,
            username  TEXT UNIQUE NOT NULL,
            pw_hash   TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def register_user(
    username: str,
    password: str,
    db_path: Path = _DEFAULT_DB,
) -> str:
    """Create a new user. Returns user_id. Raises ValueError if username taken."""
    if len(password) < 6:
        raise ValueError("密碼至少需要 6 個字元")
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    try:
        with _conn(db_path) as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, pw_hash, created_at) VALUES (?,?,?,?)",
                (user_id, username.strip(), pw_hash, time.time()),
            )
    except sqlite3.IntegrityError:
        raise ValueError("用戶名已存在")
    return user_id


def authenticate(
    username: str,
    password: str,
    db_path: Path = _DEFAULT_DB,
) -> Optional[str]:
    """Return user_id if credentials are valid, else None."""
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT user_id, pw_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row and bcrypt.checkpw(password.encode(), row[1].encode()):
        return row[0]
    return None


def user_exists(db_path: Path = _DEFAULT_DB) -> bool:
    """Return True if at least one user account exists."""
    with _conn(db_path) as conn:
        return conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None
