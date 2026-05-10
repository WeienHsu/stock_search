from __future__ import annotations

from typing import Callable

import pandas as pd


def compute_holdings_pnl(
    holdings: list[dict],
    _price_fn: Callable[[str], pd.DataFrame] | None = None,
) -> dict:
    """Compute unrealized P&L for holdings using live quotes.

    Args:
        holdings: list of {ticker, quantity, avg_cost}
        _price_fn: injectable price fetcher for tests; defaults to fetch_quote

    Returns:
        {items: [...enriched], summary: {count, total_cost, market_value, ...}}
    """
    if _price_fn is None:
        from src.data.price_fetcher import fetch_quote
        _price_fn = fetch_quote

    items = []
    for h in holdings:
        ticker = str(h.get("ticker") or "").strip()
        quantity = _to_float(h.get("quantity"))
        avg_cost = _to_float(h.get("avg_cost"))
        if not ticker or quantity is None or avg_cost is None:
            continue
        current_price = _fetch_current_price(ticker, _price_fn)
        items.append(_compute_item_pnl(ticker, quantity, avg_cost, current_price))

    return {"items": items, "summary": _summarize_pnl_items(items)}


def _fetch_current_price(ticker: str, price_fn: Callable) -> float | None:
    try:
        df = price_fn(ticker)
        if df is not None and not df.empty and "close" in df.columns:
            return float(df["close"].iloc[-1])
    except Exception:
        pass
    return None


def _compute_item_pnl(
    ticker: str,
    quantity: float,
    avg_cost: float,
    current_price: float | None,
) -> dict:
    cost_basis = round(quantity * avg_cost, 2)
    result: dict = {
        "ticker": ticker,
        "quantity": quantity,
        "avg_cost": avg_cost,
        "current_price": current_price,
        "cost_basis": cost_basis,
        "market_value": None,
        "unrealized_pnl": None,
        "unrealized_pnl_pct": None,
    }
    if current_price is not None:
        market_value = quantity * current_price
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0
        result.update({
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
        })
    return result


def _summarize_pnl_items(items: list[dict]) -> dict:
    count = len(items)
    if count == 0:
        return {"count": 0, "total_cost": 0.0, "market_value": 0.0,
                "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0}

    total_cost = sum(i["cost_basis"] for i in items)
    priced = [i for i in items if i["market_value"] is not None]

    if not priced:
        return {"count": count, "total_cost": round(total_cost, 2),
                "market_value": 0.0, "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0}

    priced_cost = sum(i["cost_basis"] for i in priced)
    market_value = sum(i["market_value"] for i in priced)
    unrealized_pnl = market_value - priced_cost
    unrealized_pnl_pct = (unrealized_pnl / priced_cost * 100) if priced_cost else 0.0

    return {
        "count": count,
        "total_cost": round(total_cost, 2),
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
    }


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
