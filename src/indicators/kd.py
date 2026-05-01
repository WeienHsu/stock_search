import pandas as pd
import pandas_ta as ta


def add_kd(df: pd.DataFrame, k: int = 9, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    """Add K, D columns (Stochastic). Expects lowercase high, low, close columns."""
    df = df.copy()
    raw = ta.stoch(df["high"], df["low"], df["close"], k=k, d=d, smooth_k=smooth_k)
    if raw is None or raw.empty:
        raise ValueError(f"KD calculation failed — need at least {k} rows.")
    df["K"] = raw[f"STOCHk_{k}_{d}_{smooth_k}"]
    df["D"] = raw[f"STOCHd_{k}_{d}_{smooth_k}"]
    return df


def kd_golden_cross(df: pd.DataFrame, k_threshold: int | None = None) -> pd.Series:
    """Boolean Series: True on bars where K crosses above D (golden cross).

    k_threshold: optional gate — cross only counted when K < k_threshold (low-zone).
    """
    k, d = df["K"], df["D"]
    mask = (k.shift(1) < d.shift(1)) & (k > d)
    if k_threshold is not None:
        mask = mask & (k < k_threshold)
    return mask.fillna(False)


def kd_death_cross(df: pd.DataFrame, d_threshold: int | None = None) -> pd.Series:
    """Boolean Series: True on bars where K crosses below D (death cross).

    d_threshold: optional gate — cross only counted when K > d_threshold (high-zone).
    """
    k, d = df["K"], df["D"]
    mask = (k.shift(1) > d.shift(1)) & (k < d)
    if d_threshold is not None:
        mask = mask & (k > d_threshold)
    return mask.fillna(False)
