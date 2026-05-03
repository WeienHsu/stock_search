import pandas as pd

from src.indicators.ma import add_ma
from src.indicators.ma_analysis import (
    format_inline_label,
    ma_alignment_score,
    ma_cross_signal,
    ma_direction,
    ma_hook_forecast,
)


def test_ma_alignment_score_returns_four_for_full_bullish_stack():
    df = pd.DataFrame({
        "MA_5": [11.0],
        "MA_10": [10.0],
        "MA_20": [9.0],
        "MA_60": [8.0],
        "MA_120": [7.0],
        "MA_240": [6.0],
    })

    assert ma_alignment_score(df, [5, 10, 20, 60, 120, 240]) == 4


def test_ma_direction_uses_recent_slope():
    df = pd.DataFrame({"MA_20": [10, 10.2, 10.4, 10.6, 10.8]})

    assert ma_direction(df, 20) == "上行"


def test_ma_cross_signal_detects_golden_cross():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "close": [10.0, 11.0, 12.0],
        "MA_20": [9.0, 9.5, 11.0],
        "MA_60": [10.0, 10.0, 10.0],
    })

    events = ma_cross_signal(df, 20, 60)

    assert events == [{
        "date": "2026-01-03",
        "type": "golden_cross",
        "fast_period": 20,
        "slow_period": 60,
        "price": 12.0,
    }]


def test_ma_hook_forecast_and_inline_label():
    df = pd.DataFrame({"close": [10, 11, 12, 13, 14, 15]})

    assert ma_hook_forecast(df, 3, 2) == [14.6667, 15.0]
    assert format_inline_label({
        "date": "2026-12-04",
        "type": "golden_cross",
        "fast_period": 20,
        "slow_period": 60,
        "price": 22.28,
    }) == "月×季黃金交叉 22.28 (12/04)"


def test_add_ma_supports_120_and_240_periods():
    df = pd.DataFrame({"close": list(range(1, 251))})

    result = add_ma(df, [120, 240])

    assert "MA_120" in result.columns
    assert "MA_240" in result.columns
    assert result["MA_240"].iloc[239] == sum(range(1, 241)) / 240
