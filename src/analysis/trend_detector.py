from __future__ import annotations

import pandas as pd


def detect_hh_hl(df: pd.DataFrame, pivot_window: int = 5) -> dict:
    if df.empty or not {"high", "low"}.issubset(df.columns):
        return _empty_result()

    data = df.copy().reset_index(drop=True)
    high = pd.to_numeric(data["high"], errors="coerce")
    low = pd.to_numeric(data["low"], errors="coerce")

    pivot_highs = []
    pivot_lows = []
    for idx in range(pivot_window, len(data) - pivot_window):
        h_window = high.iloc[idx - pivot_window: idx + pivot_window + 1]
        l_window = low.iloc[idx - pivot_window: idx + pivot_window + 1]
        if high.iloc[idx] == h_window.max():
            pivot_highs.append((idx, float(high.iloc[idx])))
        if low.iloc[idx] == l_window.min():
            pivot_lows.append((idx, float(low.iloc[idx])))

    latest_highs = pivot_highs[-2:]
    latest_lows = pivot_lows[-2:]
    higher_high = len(latest_highs) == 2 and latest_highs[-1][1] > latest_highs[-2][1]
    lower_high = len(latest_highs) == 2 and latest_highs[-1][1] < latest_highs[-2][1]
    higher_low = len(latest_lows) == 2 and latest_lows[-1][1] > latest_lows[-2][1]
    lower_low = len(latest_lows) == 2 and latest_lows[-1][1] < latest_lows[-2][1]

    if higher_high and higher_low:
        trend = "uptrend"
    elif lower_high and lower_low:
        trend = "downtrend"
    else:
        trend = "sideways"

    return {
        "trend": trend,
        "higher_high": higher_high,
        "higher_low": higher_low,
        "lower_high": lower_high,
        "lower_low": lower_low,
        "latest_highs": latest_highs,
        "latest_lows": latest_lows,
    }


def detect_neckline(df: pd.DataFrame, lookback: int = 60) -> list[float]:
    if df.empty or not {"high", "low"}.issubset(df.columns):
        return []
    data = df.tail(lookback)
    levels = [
        float(pd.to_numeric(data["high"], errors="coerce").quantile(0.9)),
        float(pd.to_numeric(data["low"], errors="coerce").quantile(0.1)),
        float(pd.to_numeric(data["close"], errors="coerce").median()) if "close" in data.columns else None,
    ]
    return [round(v, 2) for v in levels if v is not None and pd.notna(v)]


def trend_label(trend: str) -> str:
    return {
        "uptrend": "多頭",
        "downtrend": "空頭",
        "sideways": "盤整",
    }.get(trend, "盤整")


def _empty_result() -> dict:
    return {
        "trend": "sideways",
        "higher_high": False,
        "higher_low": False,
        "lower_high": False,
        "lower_low": False,
        "latest_highs": [],
        "latest_lows": [],
    }
