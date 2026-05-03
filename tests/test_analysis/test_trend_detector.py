import pandas as pd

from src.analysis.trend_detector import detect_hh_hl, detect_neckline, trend_label


def test_detect_hh_hl_classifies_uptrend():
    df = pd.DataFrame({
        "high": [10, 12, 9, 13, 10, 15, 12, 17, 14],
        "low": [8, 9, 7, 10, 8, 11, 9, 12, 10],
        "close": [9, 11, 8, 12, 9, 14, 11, 16, 13],
    })

    result = detect_hh_hl(df, pivot_window=1)

    assert result["trend"] == "uptrend"
    assert result["higher_high"] is True
    assert result["higher_low"] is True
    assert trend_label(result["trend"]) == "多頭"


def test_detect_neckline_returns_three_levels():
    df = pd.DataFrame({
        "high": [10, 12, 14, 16],
        "low": [8, 9, 10, 11],
        "close": [9, 11, 13, 15],
    })

    assert len(detect_neckline(df, lookback=4)) == 3
