from src.repositories import watchlist_category_repo


def test_default_categories_seed_with_multiple_rows(tmp_path):
    db_path = tmp_path / "watchlist_categories.db"

    categories = watchlist_category_repo.list_categories("user-1", db_path=db_path)

    assert len(categories) >= 7
    names = {category["name"] for category in categories}
    assert {"我的清單", "台股 ETF", "半導體", "金融", "美股"}.issubset(names)
    semiconductor = next(category for category in categories if category["name"] == "半導體")
    assert len(watchlist_category_repo.list_items("user-1", semiconductor["id"], db_path=db_path)) >= 5


def test_category_and_item_crud(tmp_path):
    db_path = tmp_path / "watchlist_categories.db"

    category = watchlist_category_repo.create_category("user-1", "測試分類", db_path=db_path)
    item = watchlist_category_repo.add_item("user-1", category["id"], "tsla", "Tesla", db_path=db_path)

    items = watchlist_category_repo.list_items("user-1", category["id"], db_path=db_path)
    assert items[0]["ticker"] == "TSLA"
    assert items[0]["name"] == "Tesla"

    watchlist_category_repo.delete_item("user-1", item["id"], db_path=db_path)
    assert watchlist_category_repo.list_items("user-1", category["id"], db_path=db_path) == []

    watchlist_category_repo.delete_category("user-1", category["id"], db_path=db_path)
    assert all(c["id"] != category["id"] for c in watchlist_category_repo.list_categories("user-1", db_path=db_path))
