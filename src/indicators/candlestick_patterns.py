from __future__ import annotations

from typing import Any

import pandas as pd


PATTERN_LABELS = {
    "bullish_engulfing": ("多頭吞噬", "bullish", "▲"),
    "bearish_engulfing": ("空頭吞噬", "bearish", "▼"),
    "doji": ("十字線", "neutral", "十"),
    "hammer": ("長下影線", "bullish", "下"),
    "shooting_star": ("長上影線", "bearish", "上"),
    "gap_up": ("跳空上漲", "bullish", "G↑"),
    "gap_down": ("跳空下跌", "bearish", "G↓"),
    "long_bullish": ("長紅K", "bullish", "長紅"),
    "long_bearish": ("長黑K", "bearish", "長黑"),
}

_PRIORITY = [
    "bullish_engulfing",
    "bearish_engulfing",
    "gap_up",
    "gap_down",
    "hammer",
    "shooting_star",
    "doji",
    "long_bullish",
    "long_bearish",
]


def detect_candlestick_patterns(df: pd.DataFrame, atr_window: int = 14) -> pd.DataFrame:
    """Detect a compact set of candlestick patterns from lowercase OHLCV data."""
    required = {"date", "open", "high", "low", "close"}
    if df.empty or not required.issubset(df.columns):
        return _empty_result()

    data = df.copy().reset_index(drop=True)
    open_ = pd.to_numeric(data["open"], errors="coerce")
    high = pd.to_numeric(data["high"], errors="coerce")
    low = pd.to_numeric(data["low"], errors="coerce")
    close = pd.to_numeric(data["close"], errors="coerce")

    body = (close - open_).abs()
    candle_range = (high - low).replace(0, pd.NA)
    upper_shadow = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_shadow = pd.concat([open_, close], axis=1).min(axis=1) - low
    prev_open = open_.shift(1)
    prev_close = close.shift(1)
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_bearish = prev_close < prev_open
    prev_bullish = prev_close > prev_open
    bullish = close > open_
    bearish = close < open_

    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    avg_tr = true_range.rolling(atr_window, min_periods=max(3, atr_window // 2)).mean()

    flags: dict[str, pd.Series] = {
        "bullish_engulfing": (
            prev_bearish & bullish & (open_ <= prev_close) & (close >= prev_open)
        ).fillna(False),
        "bearish_engulfing": (
            prev_bullish & bearish & (open_ >= prev_close) & (close <= prev_open)
        ).fillna(False),
        "doji": ((body / candle_range) <= 0.1).fillna(False),
        "hammer": (
            (lower_shadow >= body * 2)
            & (upper_shadow <= body * 1.2)
            & ((body / candle_range) <= 0.35)
        ).fillna(False),
        "shooting_star": (
            (upper_shadow >= body * 2)
            & (lower_shadow <= body * 1.2)
            & ((body / candle_range) <= 0.35)
        ).fillna(False),
        "gap_up": (low > prev_high).fillna(False),
        "gap_down": (high < prev_low).fillna(False),
        "long_bullish": (bullish & (body > avg_tr * 1.5)).fillna(False),
        "long_bearish": (bearish & (body > avg_tr * 1.5)).fillna(False),
    }

    rows: list[dict[str, Any]] = []
    for idx, row in data.iterrows():
        for pattern in _PRIORITY:
            if bool(flags[pattern].iloc[idx]):
                label, implication, marker = PATTERN_LABELS[pattern]
                rows.append({
                    "date": str(row["date"])[:10],
                    "pattern": pattern,
                    "label": label,
                    "implication": implication,
                    "marker": marker,
                    "price": _marker_price(row, implication),
                })
                break

    if not rows:
        return _empty_result()
    return pd.DataFrame(rows)


def _marker_price(row: pd.Series, implication: str) -> float:
    if implication == "bearish":
        return float(row["high"]) * 1.012
    if implication == "bullish":
        return float(row["low"]) * 0.988
    return float(row["close"])


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "pattern", "label", "implication", "marker", "price"])
