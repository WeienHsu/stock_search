from __future__ import annotations

from typing import Any

from src.sentiment.scorers.vader import score_texts


def source_from_articles(articles: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [
        f"{article.get('headline', '')} {article.get('summary', '')}".strip()
        for article in articles
    ]
    scored = score_texts(texts)
    return {
        "source": "news",
        "title": "News",
        "score": scored["score"],
        "label": scored["label"],
        "count": scored["article_count"],
        "status": "ok" if scored["article_count"] else "empty",
        "message": "",
    }
