from __future__ import annotations

import os
from typing import Any

from src.sentiment.scorers.vader import score_texts
from src.sentiment.sources.common import fetch_json, query_url


def fetch_reddit_sentiment(ticker: str) -> dict[str, Any]:
    symbol = ticker.split(".")[0].upper()
    texts = _fetch_praw_posts(symbol) or _fetch_web_json_posts(symbol)
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


def _fetch_web_json_posts(symbol: str) -> list[str]:
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
    return texts


def _fetch_praw_posts(symbol: str) -> list[str]:
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("REDDIT_REFRESH_TOKEN", "").strip()
    if not client_id or not client_secret or not refresh_token:
        return []
    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            user_agent=os.getenv("REDDIT_USER_AGENT", "stock-search/1.0"),
        )
        return [
            f"{post.title} {getattr(post, 'selftext', '')}".strip()
            for post in reddit.subreddit("all").search(
                f"{symbol} stock",
                sort="new",
                time_filter="week",
                limit=10,
            )
        ]
    except Exception:
        return []
