import pandas as pd


def add_ma(df: pd.DataFrame, periods: list[int] = (5, 10, 20, 60)) -> pd.DataFrame:
    """Add MA_{n} columns for each period. Expects lowercase 'close' column."""
    df = df.copy()
    for n in periods:
        df[f"MA_{n}"] = df["close"].rolling(n).mean()
    return df
