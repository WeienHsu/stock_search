from src.repositories import watchlist_category_repo


def test_default_categories_seed_with_multiple_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_categories.db"
    monkeypatch.setattr(watchlist_category_repo, "get_watchlist", lambda user_id: [])

    categories = watchlist_category_repo.list_categories("user-1", db_path=db_path)

    assert len(categories) >= 7
    names = {category["name"] for category in categories}
    assert {"自選清單", "台股 ETF", "半導體", "金融", "美股"}.issubset(names)
    semiconductor = next(category for category in categories if category["name"] == "半導體")
    assert len(watchlist_category_repo.list_items("user-1", semiconductor["id"], db_path=db_path)) >= 5


def test_category_and_item_crud(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_categories.db"
    monkeypatch.setattr(
        watchlist_category_repo,
        "get_watchlist",
        lambda user_id: [{"ticker": "TSLA", "name": "Tesla from master"}],
    )

    category = watchlist_category_repo.create_category("user-1", "測試分類", db_path=db_path)
    item = watchlist_category_repo.add_item("user-1", category["id"], "tsla", "Tesla", db_path=db_path)

    items = watchlist_category_repo.list_items("user-1", category["id"], db_path=db_path)
    assert items[0]["ticker"] == "TSLA"
    assert items[0]["name"] == "Tesla from master"

    watchlist_category_repo.delete_item("user-1", item["id"], db_path=db_path)
    assert watchlist_category_repo.list_items("user-1", category["id"], db_path=db_path) == []

    watchlist_category_repo.delete_category("user-1", category["id"], db_path=db_path)
    assert all(c["id"] != category["id"] for c in watchlist_category_repo.list_categories("user-1", db_path=db_path))


def test_existing_my_list_category_is_renamed_to_watchlist(tmp_path, monkeypatch):
    db_path = tmp_path / "watchlist_categories.db"
    monkeypatch.setattr(watchlist_category_repo, "get_watchlist", lambda user_id: [])
    with watchlist_category_repo._conn(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlist_categories (id, user_id, name, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("cat-old", "user-1", "我的清單", 0, 1.0, 1.0),
        )

    categories = watchlist_category_repo.list_categories("user-1", db_path=db_path)

    assert any(category["name"] == "自選清單" for category in categories)
    assert all(category["name"] != "我的清單" for category in categories)
