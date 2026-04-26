import pandas as pd
import pandas_ta as ta


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Add atr_{period} column. Expects lowercase high, low, close columns."""
    df = df.copy()
    raw = ta.atr(df["high"], df["low"], df["close"], length=period)
    if raw is None:
        raise ValueError(f"ATR calculation failed — need at least {period} rows.")
    df[f"atr_{period}"] = raw
    return df
