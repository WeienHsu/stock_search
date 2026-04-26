from typing import Any
import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd


def _detect_macd_hist_converging(df: pd.DataFrame, n_bars: int, recovery_pct: float) -> bool:
    if "histogram" not in df.columns:
        raise ValueError("Missing 'histogram' column. Call add_macd() first.")
    if len(df) < n_bars + 1:
        return False

    hist = df["histogram"].iloc[-(n_bars + 1):]
    if hist.isna().any():
        return False

    recent = hist.iloc[-n_bars:]
    if (recent >= 0).any():
        return False

    for i in range(1, len(recent)):
        if recent.iloc[i] <= recent.iloc[i - 1]:
            return False

    lookback = df["histogram"].iloc[-20:] if len(df) >= 20 else df["histogram"]
    neg_vals = lookback[lookback < 0]
    if neg_vals.empty:
        return False
    trough = neg_vals.min()
    threshold = abs(trough) * (1 - recovery_pct)
    return abs(recent.iloc[-1]) < threshold


def _build_kd_prefilter_mask(df: pd.DataFrame, window: int, kd_k_threshold: int) -> pd.Series:
    k = df["K"]
    d = df["D"]
    kd_signal = (k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)
    mask = pd.Series(False, index=df.index)
    for offset in range(0, window + 1):
        mask = mask | kd_signal.shift(offset).fillna(False)
    return mask


def detect_strategy_d(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
) -> bool:
    """Return True if Strategy D signal fires on the latest bar."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    if not _detect_macd_hist_converging(df, n_bars=n_bars, recovery_pct=recovery_pct):
        return False

    window_df = df.iloc[-(kd_window + 1):]
    k = window_df["K"]
    d = window_df["D"]
    kd_fired = ((k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)).any()
    return bool(kd_fired)


def scan_strategy_d(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
) -> pd.DataFrame:
    """Scan entire history, return DataFrame of all signal dates."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    hist = df["histogram"]
    converging_idxs: set[int] = set()

    for i in range(n_bars, len(df)):
        recent = hist.iloc[i - n_bars + 1: i + 1]
        if recent.isna().any():
            continue
        if (recent >= 0).any():
            continue
        converging = all(recent.iloc[j] > recent.iloc[j - 1] for j in range(1, len(recent)))
        if not converging:
            continue
        lb_start = max(0, i - 19)
        lookback = hist.iloc[lb_start: i + 1]
        neg_vals = lookback[lookback < 0]
        if neg_vals.empty:
            continue
        trough = neg_vals.min()
        threshold = abs(trough) * (1 - recovery_pct)
        if abs(recent.iloc[-1]) < threshold:
            converging_idxs.add(i)

    converging_mask = pd.Series(False, index=df.index)
    if converging_idxs:
        converging_mask.iloc[list(converging_idxs)] = True

    kd_mask = _build_kd_prefilter_mask(df, window=kd_window, kd_k_threshold=kd_k_threshold)
    signal = converging_mask & kd_mask

    cols = [c for c in ["date", "close", "K", "D", "macd_line", "signal_line", "histogram"]
            if c in df.columns]
    return df[signal][cols].reset_index(drop=True)


def prepare_df(df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    """Add all indicators needed for Strategy D."""
    df = add_macd(df,
                  fast=params.get("macd_fast", 12),
                  slow=params.get("macd_slow", 26),
                  signal=params.get("macd_signal", 9))
    df = add_kd(df,
                k=params.get("kd_k", 9),
                d=params.get("kd_d", 3),
                smooth_k=params.get("kd_smooth_k", 3))
    return df


class StrategyD(StrategyBase):
    strategy_id = "strategy_d"

    def default_params(self) -> dict[str, Any]:
        return {
            "kd_window": 10,
            "n_bars": 3,
            "recovery_pct": 0.7,
            "kd_k_threshold": 20,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "kd_k": 9,
            "kd_d": 3,
            "kd_smooth_k": 3,
        }

    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        p = {**self.default_params(), **params}
        df = prepare_df(df, p)

        signal_df = scan_strategy_d(
            df,
            kd_window=p["kd_window"],
            n_bars=p["n_bars"],
            recovery_pct=p["recovery_pct"],
            kd_k_threshold=p["kd_k_threshold"],
        )

        signals: list[Signal] = []
        for _, row in signal_df.iterrows():
            date_val = str(row["date"])[:10] if "date" in row else ""
            signals.append(Signal(
                date=date_val,
                signal_type="buy",
                strategy_id=self.strategy_id,
                metadata={"close": float(row.get("close", 0))},
            ))
        return signals


register("strategy_d", StrategyD)
