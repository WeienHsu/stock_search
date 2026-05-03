from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from src.repositories.watchlist_repo import add_ticker as add_watchlist_ticker
from src.repositories.watchlist_repo import get_watchlist

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "watchlist_categories.db"

DEFAULT_CATEGORIES: list[tuple[str, list[tuple[str, str]]]] = [
    ("自選清單", []),
    ("台股 ETF", [
        ("0050.TW", "元大台灣50"),
        ("00878.TW", "國泰永續高股息"),
        ("00922.TW", "國泰台灣領袖50"),
        ("00980A.TW", "中信AI晶片正2"),
        ("00981A.TW", "中信台灣科技優選正2"),
    ]),
    ("半導體", [
        ("2330.TW", "台積電"),
        ("2303.TW", "聯電"),
        ("2454.TW", "聯發科"),
        ("3037.TW", "欣興"),
        ("3711.TW", "日月光投控"),
    ]),
    ("金融", [
        ("2881.TW", "富邦金"),
        ("2882.TW", "國泰金"),
        ("2884.TW", "玉山金"),
        ("2886.TW", "兆豐金"),
        ("2891.TW", "中信金"),
    ]),
    ("中概", [
        ("2317.TW", "鴻海"),
        ("2324.TW", "仁寶"),
        ("2354.TW", "鴻準"),
        ("4938.TW", "和碩"),
        ("9904.TW", "寶成"),
    ]),
    ("美股", [
        ("NVDA", "NVIDIA"),
        ("TSLA", "Tesla"),
        ("MSFT", "Microsoft"),
        ("GOOGL", "Alphabet"),
        ("META", "Meta"),
    ]),
    ("港股", [
        ("0700.HK", "騰訊控股"),
        ("9988.HK", "阿里巴巴"),
        ("3690.HK", "美團"),
        ("0939.HK", "建設銀行"),
        ("1299.HK", "友邦保險"),
    ]),
]


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_categories (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            name       TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            UNIQUE(user_id, name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_items (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            category_id TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            name        TEXT NOT NULL DEFAULT '',
            sort_order  INTEGER NOT NULL,
            note        TEXT NOT NULL DEFAULT '',
            created_at  REAL NOT NULL,
            FOREIGN KEY(category_id) REFERENCES watchlist_categories(id) ON DELETE CASCADE,
            UNIQUE(user_id, category_id, ticker)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_categories_user ON watchlist_categories(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_items_category ON watchlist_items(category_id, sort_order)")
    conn.commit()
    return conn


def ensure_default_categories(user_id: str, *, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        _migrate_primary_category_name(conn, user_id)
        existing = conn.execute(
            "SELECT COUNT(*) FROM watchlist_categories WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        if existing:
            return
        for idx, (name, items) in enumerate(DEFAULT_CATEGORIES):
            category_id = _insert_category(conn, user_id, name, idx)
            for item_idx, (ticker, item_name) in enumerate(items):
                _insert_item(conn, user_id, category_id, ticker, item_name, item_idx)


def list_categories(user_id: str, *, db_path: Path = _DEFAULT_DB) -> list[dict[str, Any]]:
    ensure_default_categories(user_id, db_path=db_path)
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM watchlist_categories
            WHERE user_id = ?
            ORDER BY sort_order ASC, name ASC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_items(user_id: str, category_id: str, *, db_path: Path = _DEFAULT_DB) -> list[dict[str, Any]]:
    ensure_default_categories(user_id, db_path=db_path)
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM watchlist_items
            WHERE user_id = ? AND category_id = ?
            ORDER BY sort_order ASC, ticker ASC
            """,
            (user_id, category_id),
        ).fetchall()
    return _join_watchlist_metadata(user_id, [dict(row) for row in rows])


def create_category(user_id: str, name: str, *, db_path: Path = _DEFAULT_DB) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("category name is required")
    ensure_default_categories(user_id, db_path=db_path)
    with _conn(db_path) as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM watchlist_categories WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        category_id = _insert_category(conn, user_id, clean_name, int(max_order) + 1)
        row = conn.execute("SELECT * FROM watchlist_categories WHERE id = ?", (category_id,)).fetchone()
    return dict(row)


def delete_category(user_id: str, category_id: str, *, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "DELETE FROM watchlist_categories WHERE user_id = ? AND id = ?",
            (user_id, category_id),
        )


def add_item(
    user_id: str,
    category_id: str,
    ticker: str,
    name: str = "",
    note: str = "",
    *,
    db_path: Path = _DEFAULT_DB,
) -> dict[str, Any]:
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        raise ValueError("ticker is required")
    with _conn(db_path) as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM watchlist_items WHERE user_id = ? AND category_id = ?",
            (user_id, category_id),
        ).fetchone()[0]
        item_id = _insert_item(conn, user_id, category_id, clean_ticker, name.strip(), int(max_order) + 1, note.strip())
        row = conn.execute("SELECT * FROM watchlist_items WHERE id = ?", (item_id,)).fetchone()
    return _join_watchlist_metadata(user_id, [dict(row)])[0]


def delete_item(user_id: str, item_id: str, *, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "DELETE FROM watchlist_items WHERE user_id = ? AND id = ?",
            (user_id, item_id),
        )


def is_primary_watchlist_category(category: dict[str, Any]) -> bool:
    return str(category.get("name", "")).strip() in {"自選清單", "我的清單"}


def _join_watchlist_metadata(user_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    watchlist_by_ticker = {
        str(item.get("ticker", "")).upper(): item
        for item in get_watchlist(user_id)
    }
    joined = []
    for row in rows:
        ticker = str(row.get("ticker", "")).upper()
        master = watchlist_by_ticker.get(ticker, {})
        item = dict(row)
        item["ticker"] = ticker
        item["name"] = master.get("name") or row.get("name", "")
        item["note"] = row.get("note", "")
        joined.append(item)
    return joined


def _migrate_primary_category_name(conn: sqlite3.Connection, user_id: str) -> None:
    old_row = conn.execute(
        "SELECT id FROM watchlist_categories WHERE user_id = ? AND name = ?",
        (user_id, "我的清單"),
    ).fetchone()
    if not old_row:
        return

    new_row = conn.execute(
        "SELECT id FROM watchlist_categories WHERE user_id = ? AND name = ?",
        (user_id, "自選清單"),
    ).fetchone()
    if not new_row:
        conn.execute(
            "UPDATE watchlist_categories SET name = ?, updated_at = ? WHERE id = ?",
            ("自選清單", time.time(), old_row["id"]),
        )
        return

    old_items = conn.execute(
        "SELECT ticker, name FROM watchlist_items WHERE user_id = ? AND category_id = ?",
        (user_id, old_row["id"]),
    ).fetchall()
    for item in old_items:
        add_watchlist_ticker(user_id, str(item["ticker"]), str(item["name"] or ""))
    conn.execute(
        "DELETE FROM watchlist_items WHERE user_id = ? AND category_id = ?",
        (user_id, old_row["id"]),
    )
    conn.execute(
        "DELETE FROM watchlist_categories WHERE user_id = ? AND id = ?",
        (user_id, old_row["id"]),
    )


def _insert_category(conn: sqlite3.Connection, user_id: str, name: str, sort_order: int) -> str:
    now = time.time()
    category_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT OR IGNORE INTO watchlist_categories (
            id, user_id, name, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (category_id, user_id, name, sort_order, now, now),
    )
    row = conn.execute(
        "SELECT id FROM watchlist_categories WHERE user_id = ? AND name = ?",
        (user_id, name),
    ).fetchone()
    return str(row["id"])


def _insert_item(
    conn: sqlite3.Connection,
    user_id: str,
    category_id: str,
    ticker: str,
    name: str,
    sort_order: int,
    note: str = "",
) -> str:
    item_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT OR IGNORE INTO watchlist_items (
            id, user_id, category_id, ticker, name, sort_order, note, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (item_id, user_id, category_id, ticker.strip().upper(), name, sort_order, note, time.time()),
    )
    row = conn.execute(
        """
        SELECT id FROM watchlist_items
        WHERE user_id = ? AND category_id = ? AND ticker = ?
        """,
        (user_id, category_id, ticker.strip().upper()),
    ).fetchone()
    return str(row["id"])
