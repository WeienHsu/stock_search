def sort_watchlist_items(items: list[dict]) -> list[dict]:
    """Sort watchlist: US stocks first (alphabetically), then TW stocks (alphabetically)."""
    return sorted(items, key=lambda x: (x["ticker"].endswith(".TW"), x["ticker"]))
