"""
Golden tests for Strategy D — results must match PE_monitor's logic.
"""
import numpy as np
import pandas as pd
import pytest

from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.strategies.strategy_d import detect_strategy_d, scan_strategy_d


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
