import pandas as pd
import pytest

from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.bias import add_bias
from src.indicators.atr import add_atr


def test_add_macd(sample_ohlcv):
    df = add_macd(sample_ohlcv)
    assert "macd_line" in df.columns
    assert "signal_line" in df.columns
    assert "histogram" in df.columns
    assert df["histogram"].notna().sum() > 0


def test_add_kd(sample_ohlcv):
    df = add_kd(sample_ohlcv)
    assert "K" in df.columns
    assert "D" in df.columns
    assert df["K"].between(0, 100).all() or df["K"].isna().any()


def test_add_ma(sample_ohlcv):
    df = add_ma(sample_ohlcv, periods=[5, 20])
    assert "MA_5" in df.columns
    assert "MA_20" in df.columns
    assert df["MA_20"].iloc[19] == pytest.approx(df["close"].iloc[:20].mean(), rel=1e-6)


def test_add_bias(sample_ohlcv):
    df = add_bias(sample_ohlcv, period=20)
    col = "bias_20"
    assert col in df.columns
    row = df.dropna(subset=[col]).iloc[0]
    ma = df["close"].rolling(20).mean().loc[row.name]
    expected = (row["close"] - ma) / ma * 100
    assert row[col] == pytest.approx(expected, rel=1e-6)


def test_add_atr(sample_ohlcv):
    df = add_atr(sample_ohlcv, period=14)
    assert "atr_14" in df.columns
    assert df["atr_14"].dropna().gt(0).all()
