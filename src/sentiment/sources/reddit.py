from __future__ import annotations

from typing import Any

from src.sentiment.scorers.vader import score_texts
from src.sentiment.sources.common import fetch_json, query_url


def fetch_reddit_sentiment(ticker: str) -> dict[str, Any]:
    symbol = ticker.split(".")[0].upper()
    url = query_url(
        "https://www.reddit.com/search.json",
        {"q": f"{symbol} stock", "sort": "new", "limit": 10, "t": "week"},
    )
    data = fetch_json(url, timeout=5)
    posts = data.get("data", {}).get("children", []) if isinstance(data, dict) else []
    texts = []
    for post in posts:
        payload = post.get("data", {}) if isinstance(post, dict) else {}
        texts.append(f"{payload.get('title', '')} {payload.get('selftext', '')}".strip())
    scored = score_texts(texts)
    return {
        "source": "reddit",
        "title": "Reddit",
        "score": scored["score"],
        "label": scored["label"],
        "count": scored["article_count"],
        "status": "ok" if scored["article_count"] else "empty",
        "message": "",
    }
