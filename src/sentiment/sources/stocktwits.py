from __future__ import annotations

from typing import Any

from src.sentiment.scorers.vader import score_texts
from src.sentiment.sources.common import fetch_json


def fetch_stocktwits_sentiment(ticker: str) -> dict[str, Any]:
    symbol = ticker.split(".")[0].upper()
    data = fetch_json(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json", timeout=5)
    messages = data.get("messages", []) if isinstance(data, dict) else []
    texts = [str(message.get("body", "")) for message in messages if isinstance(message, dict)]
    scored = score_texts(texts[:20])
    return {
        "source": "stocktwits",
        "title": "Stocktwits",
        "score": scored["score"],
        "label": scored["label"],
        "count": scored["article_count"],
        "status": "ok" if scored["article_count"] else "empty",
        "message": "",
    }
