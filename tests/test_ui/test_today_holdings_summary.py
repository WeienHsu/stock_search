import pandas as pd

from src.risk.holdings_pnl import _compute_item_pnl, _summarize_pnl_items, compute_holdings_pnl


def _price_fn(prices: dict):
    def _fn(ticker: str) -> pd.DataFrame:
        p = prices.get(ticker)
        return pd.DataFrame({"close": [p]}) if p else pd.DataFrame()
    return _fn


def test_holdings_pnl_calculates_unrealized_pnl():
    holdings = [
        {"ticker": "2330.TW", "quantity": 10, "avg_cost": 100},
        {"ticker": "TSLA", "quantity": 2, "avg_cost": 200},
    ]
    result = compute_holdings_pnl(holdings, _price_fn=_price_fn({"2330.TW": 110, "TSLA": 190}))
    summary = result["summary"]

    assert summary["count"] == 2
    assert summary["total_cost"] == 1400.0
    assert summary["market_value"] == 1480.0
    assert summary["unrealized_pnl"] == 80.0
    assert abs(summary["unrealized_pnl_pct"] - 5.71) < 0.01


def test_holdings_pnl_skips_invalid_rows():
    # missing current price → unpriced, not skipped from count
    result = compute_holdings_pnl(
        [{"ticker": "2330.TW", "quantity": 10}],
        _price_fn=_price_fn({}),
    )
    assert result["summary"]["count"] == 0  # quantity present but avg_cost missing


def test_holdings_pnl_graceful_when_no_price_available():
    result = compute_holdings_pnl(
        [{"ticker": "2330.TW", "quantity": 10, "avg_cost": 100}],
        _price_fn=_price_fn({}),
    )
    summary = result["summary"]
    assert summary["count"] == 1
    assert summary["market_value"] == 0.0
    assert result["items"][0]["current_price"] is None
