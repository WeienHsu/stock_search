from __future__ import annotations

from src.repositories import user_prefs_repo

_NAMESPACE = "holdings"


def get_holdings(user_id: str) -> list[dict]:
    """Return list of holdings for user. Each item: {ticker, quantity, avg_cost}."""
    payload = user_prefs_repo.get(user_id, _NAMESPACE)
    items = payload.get("items", [])
    return [i for i in items if isinstance(i, dict)]


def save_holdings(user_id: str, items: list[dict]) -> None:
    """Persist the full holdings list, replacing any previous data."""
    validated = [_validate_item(i) for i in items if isinstance(i, dict)]
    user_prefs_repo.set(user_id, _NAMESPACE, {"items": [v for v in validated if v is not None]})


def _validate_item(item: dict) -> dict | None:
    ticker = str(item.get("ticker") or "").strip().upper()
    if not ticker:
        return None
    try:
        quantity = float(item["quantity"])
        avg_cost = float(item["avg_cost"])
    except (KeyError, TypeError, ValueError):
        return None
    if quantity <= 0 or avg_cost <= 0:
        return None
    return {"ticker": ticker, "quantity": quantity, "avg_cost": avg_cost}
