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
