import pandas as pd
import pandas_ta as ta


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Add macd_line, signal_line, histogram columns. Expects lowercase 'close' column."""
    df = df.copy()
    raw = ta.macd(df["close"], fast=fast, slow=slow, signal=signal)
    if raw is None or raw.empty:
        raise ValueError(f"MACD calculation failed — need at least {slow + signal} rows.")
    df["macd_line"]   = raw[f"MACD_{fast}_{slow}_{signal}"]
    df["signal_line"] = raw[f"MACDs_{fast}_{slow}_{signal}"]
    df["histogram"]   = raw[f"MACDh_{fast}_{slow}_{signal}"]
    return df
