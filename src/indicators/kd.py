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
