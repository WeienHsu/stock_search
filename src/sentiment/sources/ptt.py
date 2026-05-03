from __future__ import annotations

import re
from html import unescape
from typing import Any

from src.sentiment.scorers.vader import score_texts
from src.sentiment.sources.common import fetch_text, query_url


def fetch_ptt_sentiment(ticker: str) -> dict[str, Any]:
    symbol = ticker.split(".")[0].upper()
    url = query_url("https://www.ptt.cc/bbs/Stock/search", {"q": symbol})
    html = fetch_text(url, timeout=5)
    titles = [
        _clean_html(match)
        for match in re.findall(r'<div class="title">\s*(.*?)\s*</div>', html, flags=re.S)
    ]
    titles = [title for title in titles if title]
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


def _clean_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(text).split())
