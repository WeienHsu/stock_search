import pandas as pd

from src.scanner import watchlist_scanner
from src.scanner.watchlist_scanner import _daily_change_pct, scan_watchlist


class StrategyStub:
    def compute(self, df, params):
        return []


def test_daily_change_pct_uses_previous_close():
    df = pd.DataFrame({"close": [100, 105]})

    assert _daily_change_pct(df) == 5.0


def test_daily_change_pct_handles_missing_previous_close():
    assert _daily_change_pct(pd.DataFrame({"close": [100]})) is None
    assert _daily_change_pct(pd.DataFrame({"close": [0, 100]})) is None


def test_scan_watchlist_returns_daily_change_pct(monkeypatch):
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=80, freq="B").strftime("%Y-%m-%d"),
        "open": [100.0] * 78 + [100.0, 105.0],
        "high": [101.0] * 78 + [101.0, 106.0],
        "low": [99.0] * 78 + [99.0, 104.0],
        "close": [100.0] * 78 + [100.0, 105.0],
        "volume": [1000] * 80,
    })
    monkeypatch.setattr(watchlist_scanner, "get_strategy", lambda strategy_id: StrategyStub())
    monkeypatch.setattr(watchlist_scanner, "fetch_prices_for_strategy", lambda ticker, years=1: df)
    monkeypatch.setattr(watchlist_scanner, "summarize_vp_context", lambda df, close: {"poc_distance_pct": None})
    monkeypatch.setattr(watchlist_scanner, "detect_hh_hl", lambda df, pivot_window=5: {"trend": "uptrend"})
    monkeypatch.setattr(watchlist_scanner, "trend_label", lambda trend: "上升")

    result = scan_watchlist([{"ticker": "2330", "name": "台積電"}], "strategy_d", {})

    assert result.iloc[0]["daily_change_pct"] == 5.0
