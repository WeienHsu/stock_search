from __future__ import annotations

import json
from typing import Any

from src.sentiment.sources.common import fetch_json, query_url

POLYMARKET_API_URL = "https://gamma-api.polymarket.com/markets"

_FINANCE_KEYWORDS = [
    "stock", "market", "nasdaq", "s&p", "dow", "spy", "qqq",
    "bull", "bear", "recession", "economy", "fed", "interest rate",
    "inflation", "gdp", "earnings", "trade war", "tariff", "equity",
    "wall street", "crypto",
]

_BULL_KEYWORDS = [
    "bull", "up", "high", "record", "rally", "positive", "gain",
    "growth", "rise", "higher", "increase", "above", "recover", "boom",
]

_BEAR_KEYWORDS = [
    "crash", "down", "recession", "bear", "decline", "drop", "fall",
    "correction", "loss", "collapse", "lower", "decrease", "below",
    "negative", "crisis", "deficit",
]


def fetch_polymarket_markets(limit: int = 100) -> list[dict[str, Any]]:
    url = query_url(POLYMARKET_API_URL, {"active": "true", "closed": "false", "limit": limit})
    data = fetch_json(url, timeout=8)
    if not isinstance(data, list):
        return []
    return [m for m in data if isinstance(m, dict) and _is_finance_market(m)]


def _is_finance_market(market: dict[str, Any]) -> bool:
    q = (market.get("question") or "").lower()
    return any(kw in q for kw in _FINANCE_KEYWORDS)


def classify_market(question: str) -> int:
    q = question.lower()
    bull = sum(1 for kw in _BULL_KEYWORDS if kw in q)
    bear = sum(1 for kw in _BEAR_KEYWORDS if kw in q)
    if bull > bear:
        return 1
    if bear > bull:
        return -1
    return 0


def market_to_score(market: dict[str, Any]) -> float | None:
    question = market.get("question", "")
    direction = classify_market(question)
    if direction == 0:
        return None

    try:
        prices_raw = market.get("outcomePrices", "[]")
        prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw

        outcomes_raw = market.get("outcomes", '["Yes","No"]')
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw

        yes_idx = next((i for i, o in enumerate(outcomes) if str(o).lower() == "yes"), 0)
        yes_price = float(prices[yes_idx])
    except (ValueError, IndexError, TypeError, json.JSONDecodeError):
        return None

    return round(direction * (yes_price - 0.5) * 2.0, 4)
