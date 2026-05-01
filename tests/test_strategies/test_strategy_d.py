"""
Golden tests for Strategy D buy and sell signals.
"""
import numpy as np
import pandas as pd
import pytest

from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.strategies.strategy_d import (
    detect_strategy_d, scan_strategy_d,
    detect_strategy_d_sell, scan_strategy_d_sell,
    diagnose_strategy_d, StrategyD,
)


def _make_df(n: int = 100, seed: int = 0) -> pd.DataFrame:
    np.random.seed(seed)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high  = close + np.abs(np.random.randn(n)) * 0.3
    low   = close - np.abs(np.random.randn(n)) * 0.3
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": close,
        "high": high, "low": low, "close": close,
        "volume": 1_000_000,
    })
    df = add_macd(df)
    df = add_kd(df)
    return df


# ── Buy signal tests ──────────────────────────────────────────────────────────

def test_detect_strategy_d_returns_bool():
    df = _make_df()
    result = detect_strategy_d(df)
    assert isinstance(result, bool)


def test_scan_returns_dataframe():
    df = _make_df(200, seed=7)
    sig_df = scan_strategy_d(df)
    assert isinstance(sig_df, pd.DataFrame)
    assert "date" in sig_df.columns


def test_detect_raises_without_indicators():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing required columns"):
        detect_strategy_d(df)


def test_signal_dates_subset_of_df_dates():
    df = _make_df(200, seed=42)
    sig_df = scan_strategy_d(df)
    if not sig_df.empty:
        all_dates = set(df["date"].tolist())
        for d in sig_df["date"]:
            assert str(d)[:10] in all_dates


def test_recovery_pct_tighter_gives_fewer_signals():
    df = _make_df(300, seed=1)
    loose  = scan_strategy_d(df, recovery_pct=0.3)
    strict = scan_strategy_d(df, recovery_pct=0.9)
    assert len(strict) <= len(loose)


# ── Sell signal tests ─────────────────────────────────────────────────────────

def test_detect_strategy_d_sell_returns_bool():
    df = _make_df()
    result = detect_strategy_d_sell(df)
    assert isinstance(result, bool)


def test_scan_sell_returns_dataframe():
    df = _make_df(200, seed=7)
    sig_df = scan_strategy_d_sell(df)
    assert isinstance(sig_df, pd.DataFrame)
    assert "date" in sig_df.columns


def test_detect_sell_raises_without_indicators():
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(ValueError, match="Missing required columns"):
        detect_strategy_d_sell(df)


def test_sell_signal_dates_subset_of_df_dates():
    df = _make_df(200, seed=42)
    sig_df = scan_strategy_d_sell(df)
    if not sig_df.empty:
        all_dates = set(df["date"].tolist())
        for d in sig_df["date"]:
            assert str(d)[:10] in all_dates


def test_sell_recovery_pct_tighter_gives_fewer_signals():
    df = _make_df(300, seed=1)
    loose  = scan_strategy_d_sell(df, recovery_pct=0.3)
    strict = scan_strategy_d_sell(df, recovery_pct=0.9)
    assert len(strict) <= len(loose)


def test_buy_and_sell_not_both_on_same_bar():
    """A single bar should not simultaneously trigger buy AND sell."""
    df = _make_df(300, seed=5)
    buy_df  = scan_strategy_d(df)
    sell_df = scan_strategy_d_sell(df)
    if buy_df.empty or sell_df.empty:
        return
    buy_dates  = set(buy_df["date"].astype(str).str[:10])
    sell_dates = set(sell_df["date"].astype(str).str[:10])
    overlap = buy_dates & sell_dates
    # Overlap should be empty: MACD histogram cannot be simultaneously
    # all-negative (buy condition) and all-positive (sell condition)
    assert len(overlap) == 0, f"Unexpected overlap on dates: {overlap}"


def test_diagnose_buy_kd_uses_cross_bar_k_not_latest_k():
    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=6, freq="B").strftime("%Y-%m-%d"),
        "K": [30.0, 25.0, 15.0, 18.0, 28.0, 35.0],
        "D": [35.0, 30.0, 20.0, 17.0, 24.0, 30.0],
        "histogram": [-0.8, -0.7, -0.6, -0.4, -0.25, -0.1],
    })

    conditions = diagnose_strategy_d(df, "2025-01-08", {
        "buy_kd_window": 3,
        "buy_kd_k_threshold": 20,
        "buy_n_bars": 3,
        "buy_recovery_pct": 0.6,
        "buy_max_violations": 1,
        "buy_lookback_bars": 6,
    })

    kd_condition = next(c for c in conditions if c["condition"].startswith("KD 黃金交叉"))
    assert kd_condition["passed"] is True
    cross_k = next(m for m in kd_condition["metrics"] if m["name"].startswith("交叉當日 K"))
    current_ref = next(m for m in kd_condition["metrics"] if m["name"].startswith("診斷日 K/D"))
    assert cross_k["actual"] == 18.0
    assert cross_k["passed"] is True
    assert current_ref["actual"].startswith("K=35.0")


def test_strategy_d_compute_uses_independent_buy_sell_params(monkeypatch):
    captured = {}

    monkeypatch.setattr("src.strategies.strategy_d.prepare_df", lambda df, params: df)

    def fake_buy(df, **kwargs):
        captured["buy"] = kwargs
        return pd.DataFrame({"date": ["2025-01-01"], "close": [100.0]})

    def fake_sell(df, **kwargs):
        captured["sell"] = kwargs
        return pd.DataFrame({"date": ["2025-01-02"], "close": [101.0]})

    monkeypatch.setattr("src.strategies.strategy_d.scan_strategy_d", fake_buy)
    monkeypatch.setattr("src.strategies.strategy_d.scan_strategy_d_sell", fake_sell)

    StrategyD().compute(pd.DataFrame({"date": ["2025-01-01"], "close": [100.0]}), {
        "buy_kd_window": 2,
        "buy_n_bars": 4,
        "buy_recovery_pct": 0.55,
        "buy_kd_k_threshold": 18,
        "buy_max_violations": 0,
        "buy_lookback_bars": 12,
        "sell_kd_window": 7,
        "sell_n_bars": 8,
        "sell_recovery_pct": 0.75,
        "sell_kd_d_threshold": 85,
        "sell_max_violations": 2,
        "sell_lookback_bars": 30,
    })

    assert captured["buy"]["kd_window"] == 2
    assert captured["buy"]["n_bars"] == 4
    assert captured["buy"]["kd_k_threshold"] == 18
    assert captured["sell"]["kd_window"] == 7
    assert captured["sell"]["n_bars"] == 8
    assert captured["sell"]["kd_d_threshold"] == 85


def test_strategy_d_compute_keeps_legacy_flat_param_fallback(monkeypatch):
    captured = {}

    monkeypatch.setattr("src.strategies.strategy_d.prepare_df", lambda df, params: df)
    def fake_buy(df, **kwargs):
        captured["buy"] = kwargs
        return pd.DataFrame()

    def fake_sell(df, **kwargs):
        captured["sell"] = kwargs
        return pd.DataFrame()

    monkeypatch.setattr("src.strategies.strategy_d.scan_strategy_d", fake_buy)
    monkeypatch.setattr("src.strategies.strategy_d.scan_strategy_d_sell", fake_sell)

    StrategyD().compute(pd.DataFrame({"date": ["2025-01-01"], "close": [100.0]}), {
        "kd_window": 5,
        "n_bars": 6,
        "recovery_pct": 0.7,
        "kd_k_threshold": 21,
        "kd_d_threshold": 82,
        "max_violations": 1,
        "lookback_bars": 24,
    })

    assert captured["buy"]["kd_window"] == 5
    assert captured["buy"]["n_bars"] == 6
    assert captured["sell"]["kd_window"] == 5
    assert captured["sell"]["n_bars"] == 6
