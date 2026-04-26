import json
from pathlib import Path
from typing import Any

from src.repositories._backends import get_user_backend

_backend = get_user_backend()
_KEY = "watchlist"

_DEFAULTS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"


def _default_watchlist() -> list[dict]:
    with open(_DEFAULTS_PATH, encoding="utf-8") as f:
        return json.load(f).get("watchlist_defaults", [])


def get_watchlist(user_id: str) -> list[dict[str, Any]]:
    return _backend.get(user_id, _KEY, default=_default_watchlist())


def save_watchlist(user_id: str, items: list[dict[str, Any]]) -> None:
    _backend.save(user_id, _KEY, items)


def add_ticker(user_id: str, ticker: str, name: str = "") -> None:
    items = get_watchlist(user_id)
    if not any(i["ticker"] == ticker for i in items):
        items.append({"ticker": ticker, "name": name})
        save_watchlist(user_id, items)


def remove_ticker(user_id: str, ticker: str) -> None:
    items = [i for i in get_watchlist(user_id) if i["ticker"] != ticker]
    save_watchlist(user_id, items)
