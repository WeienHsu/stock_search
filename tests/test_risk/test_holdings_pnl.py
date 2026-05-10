import pandas as pd
import pytest

from src.risk.holdings_pnl import (
    _compute_item_pnl,
    _summarize_pnl_items,
    _to_float,
    compute_holdings_pnl,
)


def _make_price_fn(prices: dict[str, float]):
    """Return a price fetcher that reads from a static dict."""
    def _fn(ticker: str) -> pd.DataFrame:
        price = prices.get(ticker)
        if price is None:
            return pd.DataFrame()
        return pd.DataFrame({"close": [price]})
    return _fn


def test_compute_item_pnl_with_price_calculates_correctly():
    item = _compute_item_pnl("2330.TW", 1000, 850.0, 900.0)

    assert item["ticker"] == "2330.TW"
    assert item["cost_basis"] == 850_000.0
    assert item["market_value"] == 900_000.0
    assert item["unrealized_pnl"] == 50_000.0
    assert abs(item["unrealized_pnl_pct"] - 5.882) < 0.01


def test_compute_item_pnl_without_price_leaves_pnl_as_none():
    item = _compute_item_pnl("TSLA", 100, 200.0, None)

    assert item["market_value"] is None
    assert item["unrealized_pnl"] is None
    assert item["unrealized_pnl_pct"] is None
    assert item["cost_basis"] == 20_000.0


def test_compute_item_pnl_negative_pnl():
    item = _compute_item_pnl("0050.TW", 500, 120.0, 100.0)

    assert item["unrealized_pnl"] == -10_000.0
    assert item["unrealized_pnl_pct"] < 0


def test_summarize_empty_items_returns_zero_summary():
    summary = _summarize_pnl_items([])

    assert summary["count"] == 0
    assert summary["unrealized_pnl"] == 0.0


def test_summarize_all_unpriced_items():
    items = [
        _compute_item_pnl("A", 100, 10.0, None),
        _compute_item_pnl("B", 200, 20.0, None),
    ]
    summary = _summarize_pnl_items(items)

    assert summary["count"] == 2
    assert summary["total_cost"] == 5_000.0
    assert summary["market_value"] == 0.0


def test_summarize_partial_pricing():
    items = [
        _compute_item_pnl("A", 100, 10.0, 12.0),   # priced
        _compute_item_pnl("B", 200, 20.0, None),    # unpriced
    ]
    summary = _summarize_pnl_items(items)

    assert summary["count"] == 2
    assert summary["total_cost"] == 5_000.0    # both cost bases
    assert summary["market_value"] == 1_200.0  # only priced
    assert summary["unrealized_pnl"] == 200.0  # priced only


def test_compute_holdings_pnl_end_to_end():
    holdings = [
        {"ticker": "2330.TW", "quantity": 1000, "avg_cost": 800.0},
        {"ticker": "TSLA", "quantity": 10, "avg_cost": 200.0},
    ]
    prices = {"2330.TW": 850.0, "TSLA": 190.0}
    result = compute_holdings_pnl(holdings, _price_fn=_make_price_fn(prices))

    assert result["summary"]["count"] == 2
    assert result["summary"]["market_value"] == 1000 * 850.0 + 10 * 190.0
    assert len(result["items"]) == 2


def test_compute_holdings_pnl_skips_invalid_rows():
    holdings = [
        {"ticker": "", "quantity": 100, "avg_cost": 10.0},
        {"ticker": "AAPL", "quantity": None, "avg_cost": 150.0},
        {"ticker": "MSFT", "quantity": 5, "avg_cost": 300.0},
    ]
    result = compute_holdings_pnl(holdings, _price_fn=_make_price_fn({"MSFT": 310.0}))

    assert result["summary"]["count"] == 1
    assert result["items"][0]["ticker"] == "MSFT"


def test_compute_holdings_pnl_graceful_on_fetch_error():
    def _failing_fn(ticker):
        raise ConnectionError("network down")

    holdings = [{"ticker": "2330.TW", "quantity": 100, "avg_cost": 500.0}]
    result = compute_holdings_pnl(holdings, _price_fn=_failing_fn)

    assert result["items"][0]["current_price"] is None
    assert result["summary"]["market_value"] == 0.0


def test_to_float_handles_edge_cases():
    assert _to_float(None) is None
    assert _to_float("") is None
    assert _to_float("abc") is None
    assert _to_float(100) == 100.0
    assert _to_float("3.14") == 3.14
