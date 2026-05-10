from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import streamlit as st

from src.data.dynamic_ttl import get_ttl
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache
from src.sentiment.scorers.vader import label_for_score
from src.sentiment.scorers.polymarket_scorer import fetch_polymarket_sentiment
from src.sentiment.sources.news_finnhub import source_from_articles
from src.sentiment.sources.ptt import fetch_ptt_sentiment
from src.sentiment.sources.reddit import fetch_reddit_sentiment
from src.sentiment.sources.stocktwits import fetch_stocktwits_sentiment

SourceFetcher = Callable[[str], dict[str, Any]]


def aggregate_sentiment(
    ticker: str,
    articles: list[dict[str, Any]] | None = None,
    *,
    ttl_seconds: int = 300,
    fetchers: dict[str, SourceFetcher] | None = None,
) -> dict[str, Any]:
    if fetchers is None:
        return _aggregate_sentiment_cached(ticker, articles or [], ttl_seconds)
    return _aggregate_sentiment_uncached(ticker, articles, ttl_seconds=ttl_seconds, fetchers=fetchers)


@st.cache_data(ttl=get_ttl(300), show_spinner=False)
def _aggregate_sentiment_cached(
    ticker: str,
    articles: list[dict[str, Any]],
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    return _aggregate_sentiment_uncached(ticker, articles, ttl_seconds=ttl_seconds, fetchers=None)


def _aggregate_sentiment_uncached(
    ticker: str,
    articles: list[dict[str, Any]] | None = None,
    *,
    ttl_seconds: int = 300,
    fetchers: dict[str, SourceFetcher] | None = None,
) -> dict[str, Any]:
    cache_key = f"sentiment_aggregate_{ticker.upper()}"
    cached = get_market_cache(cache_key, ttl_override=ttl_seconds)
    if isinstance(cached, dict) and cached:
        return cached

    sources = [source_from_articles(articles or [])]
    external_fetchers = fetchers or {
        "polymarket": fetch_polymarket_sentiment,
        "reddit": fetch_reddit_sentiment,
        "stocktwits": fetch_stocktwits_sentiment,
        "ptt": fetch_ptt_sentiment,
    }
    sources.extend(_fetch_external_sources(ticker, external_fetchers))
    result = _aggregate_sources(ticker, sources)
    save_market_cache(cache_key, result)
    return result


def alignment_bucket(scores: list[float]) -> str:
    if not scores:
        return "Unavailable"
    if max(scores) - min(scores) >= 1.0:
        return "Wide divergence"
    if all(score > 0.05 for score in scores):
        return "Bullish"
    if all(score < -0.05 for score in scores):
        return "Bearish"
    if max(scores) - min(scores) <= 0.3:
        return "Tight"
    return "Mixed"


def _fetch_external_sources(ticker: str, fetchers: dict[str, SourceFetcher]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, len(fetchers))) as executor:
        futures = {executor.submit(fetcher, ticker): name for name, fetcher in fetchers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results.append(_normalize_source(future.result(), name))
            except Exception:
                results.append(_unavailable_source(name, _friendly_unavailable_message(name)))
    missing = set(fetchers) - {str(result.get("source")) for result in results}
    for name in sorted(missing):
        results.append(_unavailable_source(name, _friendly_unavailable_message(name)))
    return sorted(results, key=lambda item: str(item.get("source")))


def _aggregate_sources(ticker: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_source(source, str(source.get("source", "unknown"))) for source in sources]
    valid = [
        float(source["score"])
        for source in normalized
        if source.get("status") == "ok" and isinstance(source.get("score"), (int, float))
    ]
    average = sum(valid) / len(valid) if valid else 0.0
    bucket = alignment_bucket(valid)
    return {
        "ticker": ticker.upper(),
        "score": round(average, 4),
        "label": label_for_score(average),
        "alignment": bucket,
        "source_count": len(valid),
        "sources": normalized,
    }


def _normalize_source(source: dict[str, Any], fallback_name: str) -> dict[str, Any]:
    score = source.get("score", 0.0)
    if not isinstance(score, (int, float)):
        score = 0.0
    count = source.get("count", source.get("article_count", 0))
    return {
        "source": str(source.get("source") or fallback_name),
        "title": str(source.get("title") or fallback_name.title()),
        "score": round(float(score), 4),
        "label": str(source.get("label") or label_for_score(float(score))),
        "count": int(count or 0),
        "status": str(source.get("status") or ("ok" if count else "empty")),
        "message": str(source.get("message") or ""),
    }


def _unavailable_source(name: str, message: str) -> dict[str, Any]:
    return {
        "source": name,
        "title": name.title(),
        "score": 0.0,
        "label": "neutral",
        "count": 0,
        "status": "unavailable",
        "message": message,
    }


def _friendly_unavailable_message(name: str) -> str:
    labels = {
        "polymarket": "Polymarket 暫不可用",
        "reddit": "Reddit 暫不可用",
        "stocktwits": "Stocktwits 暫不可用",
        "ptt": "PTT 暫不可用",
    }
    return labels.get(name, "來源暫不可用")
