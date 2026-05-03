from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

DEFAULT_MA_PERIODS = [5, 10, 20, 60, 120, 240]


def ma_alignment_score(df: pd.DataFrame, periods: list[int] | None = None) -> int:
    """Return a normalized 0-4 bullish MA alignment score."""
    periods = periods or [5, 10, 20, 60]
    values = _latest_ma_values(df, periods)
    if len(values) < 2:
        return 0

    bullish_pairs = sum(1 for left, right in zip(values, values[1:]) if left > right)
    max_pairs = len(values) - 1
    return int(round((bullish_pairs / max_pairs) * 4))


def ma_direction(
    df: pd.DataFrame,
    period: int,
    lookback: int = 5,
) -> Literal["上行", "下彎", "持平"]:
    col = f"MA_{period}"
    if col not in df.columns or lookback < 2:
        return "持平"
    values = pd.to_numeric(df[col], errors="coerce").dropna().tail(lookback)
    if len(values) < 2:
        return "持平"

    x = np.arange(len(values), dtype=float)
    slope = float(np.polyfit(x, values.to_numpy(dtype=float), 1)[0])
    tolerance = max(abs(float(values.iloc[-1])) * 0.0005, 1e-8)
    if slope > tolerance:
        return "上行"
    if slope < -tolerance:
        return "下彎"
    return "持平"


def ma_cross_signal(df: pd.DataFrame, fast_period: int, slow_period: int) -> list[dict]:
    fast_col = f"MA_{fast_period}"
    slow_col = f"MA_{slow_period}"
    if fast_col not in df.columns or slow_col not in df.columns or "date" not in df.columns:
        return []

    fast = pd.to_numeric(df[fast_col], errors="coerce")
    slow = pd.to_numeric(df[slow_col], errors="coerce")
    prev_fast = fast.shift(1)
    prev_slow = slow.shift(1)
    golden = (prev_fast <= prev_slow) & (fast > slow)
    death = (prev_fast >= prev_slow) & (fast < slow)

    events = []
    for idx in df.index[golden.fillna(False) | death.fillna(False)]:
        event_type = "golden_cross" if bool(golden.loc[idx]) else "death_cross"
        events.append({
            "date": str(df.loc[idx, "date"])[:10],
            "type": event_type,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "price": float(pd.to_numeric(df.loc[idx, "close"], errors="coerce")),
        })
    return events


def ma_hook_forecast(df: pd.DataFrame, period: int, n_days: int = 5) -> list[float]:
    """Forecast MA values if future closes stay flat for n days."""
    if "close" not in df.columns or period <= 0 or n_days <= 0:
        return []
    closes = pd.to_numeric(df["close"], errors="coerce").dropna().tolist()
    if len(closes) < period:
        return []

    current_close = float(closes[-1])
    forecast = []
    window = closes[-period:]
    for _ in range(n_days):
        window = window[1:] + [current_close]
        forecast.append(round(float(sum(window) / period), 4))
    return forecast


def format_inline_label(cross_event: dict) -> str:
    fast = _period_label(int(cross_event.get("fast_period", 0)))
    slow = _period_label(int(cross_event.get("slow_period", 0)))
    event = "黃金交叉" if cross_event.get("type") == "golden_cross" else "死亡交叉"
    price = float(cross_event.get("price", 0.0))
    date = str(cross_event.get("date", ""))
    date_label = date[5:].replace("-", "/") if len(date) >= 10 else date
    return f"{fast}×{slow}{event} {price:.2f} ({date_label})"


def summarize_ma_state(df: pd.DataFrame, periods: list[int] | None = None) -> dict:
    periods = periods or DEFAULT_MA_PERIODS
    score = ma_alignment_score(df, periods)
    directions = {period: ma_direction(df, period) for period in periods}
    crosses = []
    for fast, slow in [(5, 10), (10, 20), (20, 60), (60, 120), (120, 240)]:
        if fast in periods and slow in periods:
            crosses.extend(ma_cross_signal(df, fast, slow)[-3:])
    return {
        "score": score,
        "stars": "★" * score + "☆" * (4 - score),
        "directions": directions,
        "month_above_quarter": _latest_value(df, 20) > _latest_value(df, 60),
        "hook_forecast_20": ma_hook_forecast(df, 20, 5),
        "recent_crosses": crosses[-5:],
    }


def _latest_ma_values(df: pd.DataFrame, periods: list[int]) -> list[float]:
    values = []
    for period in periods:
        value = _latest_value(df, period)
        if np.isfinite(value):
            values.append(value)
    return values


def _latest_value(df: pd.DataFrame, period: int) -> float:
    col = f"MA_{period}"
    if col not in df.columns:
        return float("nan")
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(values.iloc[-1]) if not values.empty else float("nan")


def _period_label(period: int) -> str:
    labels = {5: "週", 10: "雙週", 20: "月", 60: "季", 120: "半年", 240: "年"}
    return labels.get(period, f"MA{period}")
