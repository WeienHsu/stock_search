from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from src.data.ticker_utils import normalize_ticker


@dataclass(frozen=True)
class TickerMatch:
    ticker: str
    name: str
    source: str
    score: float


_ALIASES = {
    "2330.TW": ["tsmc", "taiwan semiconductor", "台積", "台積電", "護國神山"],
    "2317.TW": ["foxconn", "hon hai", "鴻海", "富士康"],
    "0050.TW": ["taiwan 50", "元大台灣50", "台灣50"],
    "TSLA": ["tesla"],
    "NVDA": ["nvidia"],
    "MSFT": ["microsoft"],
    "GOOGL": ["alphabet", "google"],
    "META": ["meta", "facebook"],
}


def build_ticker_index(watchlist: list[dict[str, Any]], defaults: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    index: list[dict[str, Any]] = []
    for source, items in (("watchlist", watchlist), ("default", defaults)):
        for item in items:
            ticker = normalize_ticker(str(item.get("ticker", "")))
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            index.append({
                "ticker": ticker,
                "name": str(item.get("name", "")),
                "source": source,
                "aliases": _ALIASES.get(ticker, []),
            })
    return index


def default_watchlist_matches(index: list[dict[str, Any]], *, limit: int = 10) -> list[TickerMatch]:
    preferred = [item for item in index if item["source"] == "watchlist"] or index
    return [
        TickerMatch(item["ticker"], item.get("name", ""), item["source"], 1.0)
        for item in preferred[:limit]
    ]


def fuzzy_ticker_matches(query: str, index: list[dict[str, Any]], *, limit: int = 8) -> list[TickerMatch]:
    clean_query = query.strip().upper()
    if not clean_query:
        return default_watchlist_matches(index, limit=limit)

    scored: list[TickerMatch] = []
    for item in index:
        ticker = item["ticker"].upper()
        name = item.get("name", "")
        aliases = [str(alias) for alias in item.get("aliases", [])]
        score = _match_score(clean_query, ticker, name, aliases)
        if score > 0:
            scored.append(TickerMatch(item["ticker"], name, item["source"], score))
    scored.sort(key=lambda item: (-item.score, item.source != "watchlist", item.ticker))
    return scored[:limit]


def format_ticker_match(match: TickerMatch) -> str:
    return f"{match.ticker} — {match.name}" if match.name else match.ticker


def _match_score(query: str, ticker: str, name: str, aliases: list[str]) -> float:
    compact_ticker = ticker.split(".")[0]
    haystack = " ".join([ticker, compact_ticker, name, *aliases]).upper()
    if ticker == query or compact_ticker == query:
        return 3.0
    if ticker.startswith(query) or compact_ticker.startswith(query):
        return 2.7
    if query in ticker or query in compact_ticker:
        return 2.2
    if query in haystack:
        return 1.8
    ratio = SequenceMatcher(None, query, haystack).ratio()
    return ratio if ratio >= 0.45 else 0.0
