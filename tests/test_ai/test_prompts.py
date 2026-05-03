from dataclasses import dataclass

import pandas as pd

from src.ai.prompts.news_synthesizer import build_news_synthesizer_messages
from src.ai.prompts.signal_explainer import build_signal_context, build_signal_explainer_messages
from src.ai.prompts.weekly_digest import build_weekly_digest_messages


@dataclass
class SignalLayerStub:
    strategy_id: str
    label: str
    buy_dates: list[str]
    sell_dates: list[str]


def test_signal_explainer_context_compacts_recent_rows():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=70, freq="D").strftime("%Y-%m-%d"),
        "close": range(70),
        "volume": range(1000, 1070),
        "macd_line": [0.1] * 70,
        "signal_line": [0.0] * 70,
        "histogram": [0.1] * 70,
        "K": [20.0] * 70,
        "D": [18.0] * 70,
    })
    layers = [SignalLayerStub("strategy_d", "Strategy D", ["2026-01-02"], ["2026-01-03"])]

    context = build_signal_context("2330.TW", df, layers, today_buy=True, today_sell=False)
    messages = build_signal_explainer_messages(context)

    assert context["ticker"] == "2330.TW"
    assert len(context["recent_bars"]) == 60
    assert context["today_buy_signal"] is True
    assert "Strategy D" in messages[0]["content"]


def test_news_synthesizer_prompt_includes_sentiment_and_articles():
    messages = build_news_synthesizer_messages(
        "TSLA",
        [{"datetime": 1_700_000_000, "source": "Wire", "headline": "Tesla headline", "summary": "summary"}],
        {"label": "positive", "score": 0.4},
    )

    content = messages[0]["content"]
    assert "TSLA" in content
    assert "Tesla headline" in content
    assert "positive" in content


def test_weekly_digest_prompt_includes_watchlist_rows():
    messages = build_weekly_digest_messages([
        {"ticker": "NVDA", "signal": "buy", "weekly_return_pct": 2.3}
    ])

    assert "NVDA" in messages[0]["content"]
    assert "週報" in messages[0]["content"]
