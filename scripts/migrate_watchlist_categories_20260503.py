from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repositories.watchlist_category_repo import _DEFAULT_DB, _conn
from src.repositories.watchlist_repo import add_ticker


def migrate(db_path: Path = _DEFAULT_DB) -> Path | None:
    if not db_path.exists():
        _conn(db_path).close()

    backup_path = _backup(db_path)
    with _conn(db_path) as conn:
        user_ids = [
            str(row["user_id"])
            for row in conn.execute("SELECT DISTINCT user_id FROM watchlist_categories").fetchall()
        ]
        for user_id in user_ids:
            _rename_primary_category(conn, user_id)
    return backup_path


def _rename_primary_category(conn: sqlite3.Connection, user_id: str) -> None:
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
            "UPDATE watchlist_categories SET name = ?, updated_at = strftime('%s','now') WHERE id = ?",
            ("自選清單", old_row["id"]),
        )
        return

    rows = conn.execute(
        "SELECT ticker, name FROM watchlist_items WHERE user_id = ? AND category_id = ?",
        (user_id, old_row["id"]),
    ).fetchall()
    for row in rows:
        add_ticker(user_id, str(row["ticker"]), str(row["name"] or ""))
    conn.execute(
        "DELETE FROM watchlist_items WHERE user_id = ? AND category_id = ?",
        (user_id, old_row["id"]),
    )
    conn.execute(
        "DELETE FROM watchlist_categories WHERE user_id = ? AND id = ?",
        (user_id, old_row["id"]),
    )


def _backup(db_path: Path) -> Path | None:
    if not db_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}.backup_{timestamp}{db_path.suffix}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def main() -> None:
    backup_path = migrate()
    if backup_path:
        print(f"Backed up {backup_path}")
    print("Renamed primary category from 我的清單 to 自選清單.")


if __name__ == "__main__":
    main()
