import pandas as pd


def add_bias(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """
    Add bias_{period} column.
    Bias = (close - MA_n) / MA_n * 100%
    """
    df = df.copy()
    ma = df["close"].rolling(period).mean()
    df[f"bias_{period}"] = (df["close"] - ma) / ma * 100
    return df
