import pandas as pd
import yfinance as yf

from src.core.market_calendar import Granularity, cache_ttl_seconds
from src.repositories.price_cache_repo import get_price_cache, save_price_cache

_PERIOD_MAP = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "3Y": "3y",
    "5Y": "5y",
}

_INTERVAL_PERIOD_MAP = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "60m": "60d",
    "1d": None,
    "1wk": "10y",
    "1mo": "10y",
}


def fetch_prices_by_interval(ticker: str, interval: str, period: str = "6M") -> pd.DataFrame:
    """Fetch chart data for Dashboard granularity controls."""
    if interval == "1d":
        return fetch_prices_for_strategy(ticker, years=10)
    yf_period = _INTERVAL_PERIOD_MAP.get(interval)
    if not yf_period:
        return fetch_prices_for_strategy(ticker, years=10)

    ttl_granularity: Granularity = "intraday" if interval.endswith("m") else "daily"
    cache_key = f"{ticker}_{yf_period}_{interval}"
    cached = get_price_cache(
        cache_key,
        ttl_override=cache_ttl_seconds(ticker, ttl_granularity),
    )
    if cached is not None and not cached.empty:
        return _filter_period(cached, period)

    try:
        raw = yf.download(
            ticker,
            period=yf_period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        df = _normalize_df(raw, include_time=interval.endswith("m"))
        if not df.empty:
            save_price_cache(cache_key, df)
        return _filter_period(df, period)
    except Exception:
        return pd.DataFrame()


def fetch_prices(
    ticker: str,
    period: str = "6M",
    granularity: Granularity = "daily",
) -> pd.DataFrame:
    yf_period = _PERIOD_MAP.get(period, "6mo")
    cache_key = f"{ticker}_{yf_period}_{granularity}"
    cached = get_price_cache(
        cache_key,
        ttl_override=cache_ttl_seconds(ticker, granularity),
    )
    if cached is not None and not cached.empty:
        return cached

    try:
        raw = yf.download(ticker, period=yf_period, auto_adjust=True, progress=False)
        df = _normalize_df(raw)
        if not df.empty:
            save_price_cache(cache_key, df)
        return df
    except Exception:
        return pd.DataFrame()


def fetch_prices_for_strategy(ticker: str, years: int = 5) -> pd.DataFrame:
    cache_key = f"{ticker}_{years}y"
    cached = get_price_cache(
        cache_key,
        ttl_override=cache_ttl_seconds(ticker, "daily"),
    )
    if cached is not None and not cached.empty:
        return cached
    try:
        raw = yf.download(ticker, period=f"{years}y", auto_adjust=True, progress=False)
        df = _normalize_df(raw)
        if not df.empty:
            save_price_cache(cache_key, df)
        return df
    except Exception:
        return pd.DataFrame()


def fetch_quote(ticker: str) -> pd.DataFrame:
    cache_key = f"{ticker}_quote"
    cached = get_price_cache(
        cache_key,
        ttl_override=cache_ttl_seconds(ticker, "quote"),
    )
    if cached is not None and not cached.empty:
        return cached

    try:
        raw = yf.download(
            ticker,
            period="1d",
            interval="1m",
            auto_adjust=True,
            progress=False,
        )
        df = _normalize_df(raw)
        if not df.empty:
            save_price_cache(cache_key, df)
        return df
    except Exception:
        return pd.DataFrame()


def _normalize_df(data: pd.DataFrame, include_time: bool = False) -> pd.DataFrame:
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

    date_values = pd.to_datetime(df["date"])
    df["date"] = date_values.dt.strftime("%Y-%m-%d %H:%M") if include_time else date_values.dt.strftime("%Y-%m-%d")

    needed = ["date", "open", "high", "low", "close", "volume"]
    available = [c for c in needed if c in df.columns]
    return df[available].dropna().reset_index(drop=True)


def _filter_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = {
        "1M": 31,
        "3M": 92,
        "6M": 183,
        "1Y": 365,
        "3Y": 1095,
        "5Y": 1825,
    }.get(period)
    if not days or df.empty or "date" not in df.columns:
        return df
    dates = pd.to_datetime(df["date"], errors="coerce")
    cutoff = dates.max() - pd.Timedelta(days=days)
    return df[dates >= cutoff].reset_index(drop=True)
