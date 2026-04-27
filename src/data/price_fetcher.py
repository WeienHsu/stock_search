import pandas as pd
import yfinance as yf

from src.repositories.price_cache_repo import get_price_cache, save_price_cache

_PERIOD_MAP = {
    "1D": "1d",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
}


def fetch_prices(ticker: str, period: str = "6M") -> pd.DataFrame:
    yf_period = _PERIOD_MAP.get(period, "6mo")
    try:
        raw = yf.download(ticker, period=yf_period, auto_adjust=True, progress=False)
        return _normalize_df(raw)
    except Exception:
        return pd.DataFrame()


def fetch_prices_for_strategy(ticker: str, years: int = 1) -> pd.DataFrame:
    cached = get_price_cache(ticker)
    if cached is not None and not cached.empty:
        return cached
    try:
        raw = yf.download(ticker, period=f"{years}y", auto_adjust=True, progress=False)
        df = _normalize_df(raw)
        if not df.empty:
            save_price_cache(ticker, df)
        return df
    except Exception:
        return pd.DataFrame()


def _normalize_df(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()

    df = data.copy()
    df.reset_index(inplace=True)

    # yfinance 2.x returns a MultiIndex (Price, Ticker); flatten to first level
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]

    # Unify date column name
    if "datetime" in df.columns and "date" not in df.columns:
        df.rename(columns={"datetime": "date"}, inplace=True)

    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    needed = ["date", "open", "high", "low", "close", "volume"]
    available = [c for c in needed if c in df.columns]
    return df[available].dropna().reset_index(drop=True)
