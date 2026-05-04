from __future__ import annotations

import re
from html import unescape
from typing import Any

from src.sentiment.scorers.vader import score_texts
from src.sentiment.sources.common import fetch_text, query_url
from src.sentiment.sources.ptt_synonyms import query_terms_for_ticker


def fetch_ptt_sentiment(ticker: str) -> dict[str, Any]:
    titles = _fetch_titles(query_terms_for_ticker(ticker))
    scored = score_texts(titles[:20])
    return {
        "source": "ptt",
        "title": "PTT Stock",
        "score": scored["score"],
        "label": scored["label"],
        "count": scored["article_count"],
        "status": "ok" if scored["article_count"] else "empty",
        "message": "",
    }


def _fetch_titles(terms: list[str]) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    last_error: Exception | None = None
    for term in terms:
        try:
            url = query_url("https://www.ptt.cc/bbs/Stock/search", {"q": term})
            html = fetch_text(url, timeout=5)
        except Exception as exc:
            last_error = exc
            continue
        for match in re.findall(r'<div class="title">\s*(.*?)\s*</div>', html, flags=re.S):
            title = _clean_html(match)
            key = title.lower()
            if title and key not in seen:
                titles.append(title)
                seen.add(key)
    if not titles and last_error is not None:
        raise last_error
    return titles


def _clean_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(text).split())
