import pandas as pd

from src.indicators.candlestick_patterns import detect_candlestick_patterns


def test_detects_bullish_and_bearish_engulfing():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "open": [10.0, 8.8, 11.0, 12.2],
        "high": [10.2, 11.4, 12.3, 12.5],
        "low": [8.5, 8.6, 10.8, 10.0],
        "close": [9.0, 11.2, 12.0, 10.6],
        "volume": [100, 120, 130, 140],
    })

    result = detect_candlestick_patterns(df)

    assert "bullish_engulfing" in set(result["pattern"])
    assert "bearish_engulfing" in set(result["pattern"])


def test_detects_gap_up():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "open": [10.0, 11.4],
        "high": [10.5, 12.0],
        "low": [9.8, 11.2],
        "close": [10.2, 11.8],
        "volume": [100, 120],
    })

    result = detect_candlestick_patterns(df)

    assert result.iloc[-1]["pattern"] == "gap_up"
