import os
import re
import sqlite3
import logging
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger(__name__)

# Cache for PostgreSQL connection pool to avoid re-creation
_PG_POOL = None

# Primary-key columns per table, used to translate SQLite "INSERT OR REPLACE"
# into PostgreSQL "INSERT ... ON CONFLICT (<pk>) DO UPDATE SET ...".
_UPSERT_KEYS = {
    "app_settings": ("key",),
    "kv_store": ("user_id", "key"),
    "user_preferences": ("user_id", "namespace"),
    "chip_snapshots": ("ticker", "date"),
    "source_health": ("source_id",),
    "strategy_scan_events": ("user_id", "ticker", "strategy_id", "date", "signal_type"),
}

# Conflict columns for SQLite "INSERT OR IGNORE" -> "ON CONFLICT (...) DO NOTHING".
_IGNORE_KEYS = {
    "watchlist_categories": ("id",),
    "watchlist_items": ("id",),
}

# Only these tables have an auto-generated id we must read back via RETURNING.
# Every other table supplies its own id or has no id column, so appending
# "RETURNING id" there would raise "column \"id\" does not exist".
_RETURNING_ID_TABLES = {"scheduler_runs"}


def _get_pg_pool():
    global _PG_POOL
    if _PG_POOL is not None:
        return _PG_POOL

    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise ValueError("DATABASE_URL environment variable is required when STORAGE_BACKEND=postgres")

    # Min connections: 2, Max connections: 30
    _log.info("Initializing PostgreSQL Connection Pool...")
    _PG_POOL = ThreadedConnectionPool(2, 30, dsn)
    return _PG_POOL


def _translate_upsert(sql: str) -> str:
    """INSERT OR REPLACE INTO <t> (cols) ... -> INSERT INTO ... ON CONFLICT (<pk>) DO UPDATE."""
    m = re.search(r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]*)\)", sql, re.IGNORECASE)
    sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)
    if not m:
        return sql
    keys = _UPSERT_KEYS.get(m.group(1).lower())
    if not keys:
        return sql
    cols = [c.strip() for c in m.group(2).split(",")]
    updates = [c for c in cols if c not in keys]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in updates)
    return f"{sql.rstrip().rstrip(';')} ON CONFLICT ({', '.join(keys)}) DO UPDATE SET {set_clause}"


def _translate_ignore(sql: str) -> str:
    """INSERT OR IGNORE INTO <t> ... -> INSERT INTO ... ON CONFLICT (<pk>) DO NOTHING."""
    m = re.search(r"INSERT\s+OR\s+IGNORE\s+INTO\s+(\w+)", sql, re.IGNORECASE)
    keys = _IGNORE_KEYS.get(m.group(1).lower() if m else "", ("id",))
    sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)
    return f"{sql.rstrip().rstrip(';')} ON CONFLICT ({', '.join(keys)}) DO NOTHING"


def translate_sql(sql: str) -> str:
    """
    Translates SQLite-specific SQL queries to PostgreSQL compatible syntax.
    """
    # 1. Translate positional placeholder ? -> %s
    sql = sql.replace("?", "%s")

    # 2. Translate dict placeholder :name -> %(name)s
    # Ignore colons that are part of text (like url e.g., 'http://')
    sql = re.sub(r'(?<!/):([a-zA-Z_][a-zA-Z0-9_]*)', r'%(\1)s', sql)

    # 3. Handle PRAGMA table_info(users) migration check in auth_manager
    if "PRAGMA table_info(users)" in sql:
        return "SELECT 0, column_name FROM information_schema.columns WHERE table_name = 'users'"

    # 4. Translate SQLite upsert syntax into PostgreSQL ON CONFLICT clauses,
    # deriving the conflict target and updated columns from the real schema.
    if re.search(r"INSERT\s+OR\s+REPLACE\s+INTO", sql, re.IGNORECASE):
        sql = _translate_upsert(sql)
    elif re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", sql, re.IGNORECASE):
        sql = _translate_ignore(sql)

    # 5. SQLite DATATYPE and function replacements
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace("(strftime('%s','now'))", "EXTRACT(EPOCH FROM NOW())")
    sql = sql.replace("strftime('%s','now')", "EXTRACT(EPOCH FROM NOW())")

    return sql


class PostgresCursorWrapper:
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor
        self._lastrowid = None

    def execute(self, sql: str, params: Any = None):
        translated = translate_sql(sql)

        # Auto-append RETURNING id only for tables whose auto-generated id we
        # read back via lastrowid. Other tables have no id column, so RETURNING
        # there would fail.
        wants_id = False
        if translated.lstrip().upper().startswith("INSERT") and "RETURNING" not in translated.upper():
            m = re.match(r"\s*INSERT\s+INTO\s+(\w+)", translated, re.IGNORECASE)
            if m and m.group(1).lower() in _RETURNING_ID_TABLES:
                translated = f"{translated.rstrip().rstrip(';')} RETURNING id"
                wants_id = True

        try:
            self._cursor.execute(translated, params)
            if wants_id:
                row = self._cursor.fetchone()
                if row:
                    self._lastrowid = row[0]
        except Exception as e:
            _log.error(f"SQL execution failed: {translated} with params: {params}")
            raise e
        return self

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def lastrowid(self):
        return self._lastrowid

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    """
    Simulates a sqlite3 connection using a PostgreSQL connection borrowed from a ThreadedPool.
    """
    def __init__(self, pg_conn, pool):
        self._conn = pg_conn
        self._pool = pool
        self._autocommit = False

    def cursor(self):
        from psycopg2.extras import DictCursor
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=DictCursor))

    def execute(self, sql: str, params: Any = None):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        # Instead of closing physical connection, release it back to the pool
        if self._conn and self._pool:
            self._pool.putconn(self._conn)
            self._conn = None
            self._pool = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_connection(db_name: str, db_path: Optional[Path] = None) -> Any:
    """
    Returns a unified connection object (either Sqlite3 Connection or PostgresConnectionWrapper).
    Automatically reads STORAGE_BACKEND from environment.
    """
    backend = os.getenv("STORAGE_BACKEND", "json").lower()
    
    if backend == "postgres":
        pool = _get_pg_pool()
        pg_conn = pool.getconn()
        return PostgresConnectionWrapper(pg_conn, pool)
    
    # Fallback to sqlite
    # If db_path is not specified, resolve it under data/
    if db_path is None:
        db_path = Path(__file__).parents[2] / "data" / f"{db_name}.db"
        
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
