import sqlite3

from scripts import migrate_watchlist_categories_20260503 as migration
from src.repositories.watchlist_category_repo import _conn


def test_migrate_watchlist_categories_backs_up_and_renames_primary_category(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_categories.db"
    synced = []
    monkeypatch.setattr(migration, "add_ticker", lambda user_id, ticker, name="": synced.append((user_id, ticker, name)))

    with _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlist_categories (id, user_id, name, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("cat-1", "user-1", "我的清單", 0, 1.0, 1.0),
        )
        conn.execute(
            """
            INSERT INTO watchlist_items (
                id, user_id, category_id, ticker, name, sort_order, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("item-1", "user-1", "cat-1", "2330.TW", "台積電", 0, "watch", 1.0),
        )

    backup_path = migration.migrate(db_path)

    assert backup_path is not None
    assert backup_path.exists()
    assert synced == []
    with sqlite3.connect(db_path) as conn:
        category_names = [row[0] for row in conn.execute("SELECT name FROM watchlist_categories").fetchall()]
        row = conn.execute("SELECT name, note FROM watchlist_items WHERE id = ?", ("item-1",)).fetchone()
    assert category_names == ["自選清單"]
    assert row == ("台積電", "watch")


def test_migrate_merges_duplicate_old_primary_into_existing_watchlist_category(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_categories.db"
    synced = []
    monkeypatch.setattr(migration, "add_ticker", lambda user_id, ticker, name="": synced.append((user_id, ticker, name)))

    with _conn(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlist_categories (id, user_id, name, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("cat-old", "user-1", "我的清單", 0, 1.0, 1.0),
        )
        conn.execute(
            "INSERT INTO watchlist_categories (id, user_id, name, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("cat-new", "user-1", "自選清單", 1, 1.0, 1.0),
        )
        conn.execute(
            """
            INSERT INTO watchlist_items (
                id, user_id, category_id, ticker, name, sort_order, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("item-1", "user-1", "cat-old", "2330.TW", "台積電", 0, "watch", 1.0),
        )

    migration.migrate(db_path)

    assert synced == [("user-1", "2330.TW", "台積電")]
    with sqlite3.connect(db_path) as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM watchlist_categories ORDER BY name").fetchall()]
        item_count = conn.execute("SELECT COUNT(*) FROM watchlist_items").fetchone()[0]
    assert names == ["自選清單"]
    assert item_count == 0
