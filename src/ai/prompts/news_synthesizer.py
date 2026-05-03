from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.ai.provider_chain import AIProviderChain
from src.ai.providers.base import AIMessage

SYSTEM_PROMPT = (
    "你是股票新聞摘要助理。請用繁體中文，摘要要精簡、可追溯到提供的新聞，"
    "並清楚區分利多、利空或中性。不要補入未提供的事實。"
)


def build_news_synthesizer_messages(
    ticker: str,
    articles: list[dict[str, Any]],
    sentiment: dict[str, Any],
) -> list[AIMessage]:
    compact_articles = []
    for article in articles[:10]:
        ts = article.get("datetime")
        compact_articles.append({
            "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "",
            "source": article.get("source", ""),
            "headline": article.get("headline", ""),
            "summary": article.get("summary", ""),
        })

    payload = json.dumps(
        {"ticker": ticker, "vader_sentiment": sentiment, "articles": compact_articles},
        ensure_ascii=False,
        default=str,
    )
    prompt = f"""
請根據下列新聞資料輸出：
1. 三句中文摘要。
2. 利多 / 利空 / 中性 判斷與理由。
3. 一句需要進一步確認的風險或缺口。

資料：
{payload}
""".strip()
    return [{"role": "user", "content": prompt}]


def generate_news_summary(
    chain: AIProviderChain,
    ticker: str,
    articles: list[dict[str, Any]],
    sentiment: dict[str, Any],
) -> str:
    return chain.generate(
        build_news_synthesizer_messages(ticker, articles, sentiment),
        system=SYSTEM_PROMPT,
        temperature=0.2,
    )
