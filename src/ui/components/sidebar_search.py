from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from src.data.ticker_utils import normalize_ticker


def build_search_candidates(watchlist: list[dict[str, Any]], defaults: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    candidates: list[dict[str, str]] = []
    for item in [*watchlist, *defaults]:
        ticker = normalize_ticker(str(item.get("ticker", "")))
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        candidates.append({"ticker": ticker, "name": str(item.get("name", ""))})
    return sorted(candidates, key=lambda item: item["ticker"])


def fuzzy_ticker_matches(query: str, candidates: list[dict[str, str]], *, limit: int = 8) -> list[dict[str, str]]:
    clean_query = query.strip().upper()
    if not clean_query:
        return candidates[:limit]
    scored = []
    for item in candidates:
        ticker = item["ticker"].upper()
        name = item.get("name", "").upper()
        haystack = f"{ticker} {name}"
        score = _match_score(clean_query, ticker, haystack)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda row: (-row[0], row[1]["ticker"]))
    return [item for _, item in scored[:limit]]


def format_candidate(item: dict[str, str]) -> str:
    name = item.get("name", "")
    return f"{item['ticker']} — {name}" if name else item["ticker"]


def _match_score(query: str, ticker: str, haystack: str) -> float:
    if ticker == query:
        return 2.0
    if ticker.startswith(query):
        return 1.8
    if query in ticker:
        return 1.5
    if query in haystack:
        return 1.2
    ratio = SequenceMatcher(None, query, haystack).ratio()
    return ratio if ratio >= 0.45 else 0.0
