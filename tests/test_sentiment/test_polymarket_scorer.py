from __future__ import annotations

import pytest

from src.sentiment.scorers.polymarket_scorer import fetch_polymarket_sentiment


def _make_market(question: str, yes_price: float, volume: float = 10_000) -> dict:
    return {
        "question": question,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": f'["{yes_price}", "{round(1 - yes_price, 4)}"]',
        "volume": str(volume),
    }


# ── fetch_polymarket_sentiment ────────────────────────────────────────────────


def test_fetch_polymarket_sentiment_ok(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    markets = [_make_market("Will S&P 500 rally to a record high?", yes_price=0.75, volume=50_000)]
    monkeypatch.setattr(scorer, "fetch_polymarket_markets", lambda: markets)

    result = fetch_polymarket_sentiment("TSLA")

    assert result["source"] == "polymarket"
    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["score"] > 0
    assert result["label"] in ("positive", "neutral", "negative")


def test_fetch_polymarket_sentiment_ticker_agnostic(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    markets = [_make_market("Will S&P 500 rally?", yes_price=0.6, volume=10_000)]
    monkeypatch.setattr(scorer, "fetch_polymarket_markets", lambda: markets)

    result_tsla = fetch_polymarket_sentiment("TSLA")
    result_2330 = fetch_polymarket_sentiment("2330.TW")

    # Score is macro/ticker-agnostic, so both should be identical given same monkeypatch
    assert result_tsla["score"] == result_2330["score"]


def test_fetch_polymarket_sentiment_empty_markets(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    monkeypatch.setattr(scorer, "fetch_polymarket_markets", lambda: [])

    result = fetch_polymarket_sentiment("TSLA")
    assert result["status"] == "empty"
    assert result["count"] == 0
    assert result["score"] == 0.0


def test_fetch_polymarket_sentiment_all_neutral_markets(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    # All markets have neutral direction → market_to_score returns None
    markets = [{"question": "Will it rain tomorrow?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.5","0.5"]', "volume": "1000"}]
    monkeypatch.setattr(scorer, "fetch_polymarket_markets", lambda: markets)

    result = fetch_polymarket_sentiment("TSLA")
    assert result["status"] == "empty"


def test_fetch_polymarket_sentiment_handles_exception(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    def _fail():
        raise ConnectionError("network down")

    monkeypatch.setattr(scorer, "fetch_polymarket_markets", _fail)

    result = fetch_polymarket_sentiment("TSLA")
    assert result["status"] == "error"
    assert result["score"] == 0.0
    assert "network down" in result["message"]


def test_fetch_polymarket_sentiment_weighted_by_volume(monkeypatch):
    import src.sentiment.scorers.polymarket_scorer as scorer

    markets = [
        _make_market("Will stocks rally?", yes_price=0.9, volume=100_000),  # strong bullish, big vol
        _make_market("Will markets crash and decline?", yes_price=0.9, volume=100),   # strong bearish, tiny vol
    ]
    monkeypatch.setattr(scorer, "fetch_polymarket_markets", lambda: markets)

    result = fetch_polymarket_sentiment("TSLA")
    # Bullish market dominates due to larger volume
    assert result["score"] > 0
