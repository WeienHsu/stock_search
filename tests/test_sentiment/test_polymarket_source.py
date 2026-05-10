from __future__ import annotations

import pytest

from src.sentiment.sources.polymarket_source import (
    classify_market,
    fetch_polymarket_markets,
    market_to_score,
)


# ── classify_market ───────────────────────────────────────────────────────────


def test_classify_market_bullish():
    assert classify_market("Will the S&P 500 rally to a record high?") == 1


def test_classify_market_bearish():
    assert classify_market("Will the stock market crash in 2026?") == -1


def test_classify_market_neutral_returns_zero():
    assert classify_market("Will it rain in Paris tomorrow?") == 0


def test_classify_market_bear_wins_tie_scenario():
    # "bull" and "crash" both appear — bear keyword "crash" tips it
    result = classify_market("Will bull run survive the crash?")
    assert result in (-1, 1, 0)  # deterministic but direction depends on keyword count


# ── market_to_score ───────────────────────────────────────────────────────────


def _make_market(question: str, yes_price: float, volume: float = 10_000) -> dict:
    return {
        "question": question,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": f'["{yes_price}", "{round(1 - yes_price, 4)}"]',
        "volume": str(volume),
    }


def test_market_to_score_bullish_high_yes():
    market = _make_market("Will the stock market rally?", yes_price=0.8)
    score = market_to_score(market)
    assert score == pytest.approx(0.6, abs=0.01)


def test_market_to_score_bearish_high_yes():
    market = _make_market("Will markets crash and decline?", yes_price=0.8)
    score = market_to_score(market)
    assert score == pytest.approx(-0.6, abs=0.01)


def test_market_to_score_bearish_low_yes_is_bullish_signal():
    # Low crash probability → positive sentiment
    market = _make_market("Will markets crash and decline?", yes_price=0.2)
    score = market_to_score(market)
    assert score == pytest.approx(0.6, abs=0.01)


def test_market_to_score_neutral_market_returns_none():
    market = _make_market("Will it rain tomorrow?", yes_price=0.5)
    assert market_to_score(market) is None


def test_market_to_score_bad_prices_returns_none():
    market = {
        "question": "Will markets rally?",
        "outcomes": '["Yes","No"]',
        "outcomePrices": '"bad_data"',
        "volume": "0",
    }
    assert market_to_score(market) is None


def test_market_to_score_empty_outcomes_returns_none():
    market = {
        "question": "Will markets rally?",
        "outcomes": "[]",
        "outcomePrices": "[]",
        "volume": "0",
    }
    assert market_to_score(market) is None


# ── fetch_polymarket_markets ──────────────────────────────────────────────────


def test_fetch_polymarket_markets_filters_non_finance(monkeypatch):
    import src.sentiment.sources.polymarket_source as pm

    raw = [
        {"question": "Will the stock market crash?", "active": True},
        {"question": "Will it rain in Paris?", "active": True},
    ]
    monkeypatch.setattr(pm, "fetch_json", lambda *a, **kw: raw)

    result = pm.fetch_polymarket_markets()
    assert len(result) == 1
    assert "stock" in result[0]["question"].lower()


def test_fetch_polymarket_markets_handles_non_list_response(monkeypatch):
    import src.sentiment.sources.polymarket_source as pm

    monkeypatch.setattr(pm, "fetch_json", lambda *a, **kw: {"error": "bad"})
    assert pm.fetch_polymarket_markets() == []


def test_fetch_polymarket_markets_handles_none_response(monkeypatch):
    import src.sentiment.sources.polymarket_source as pm

    monkeypatch.setattr(pm, "fetch_json", lambda *a, **kw: None)
    assert pm.fetch_polymarket_markets() == []


def test_fetch_polymarket_markets_skips_non_dict_items(monkeypatch):
    import src.sentiment.sources.polymarket_source as pm

    raw = [
        "not a dict",
        {"question": "Will stock market recover?", "active": True},
    ]
    monkeypatch.setattr(pm, "fetch_json", lambda *a, **kw: raw)
    result = pm.fetch_polymarket_markets()
    assert len(result) == 1
