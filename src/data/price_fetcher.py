from collections.abc import Callable

import pandas as pd
import yfinance as yf

from src.core.market_calendar import Granularity, cache_ttl_seconds
from src.data.ticker_utils import normalize_ticker_with_fallback
from src.repositories.price_cache_repo import get_price_cache, save_price_cache
from src.repositories.ticker_resolution_repo import get_resolved_ticker, save_ticker_resolution

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
    df = _fetch_with_fallback(
        ticker,
        cache_key=lambda candidate: f"{candidate}_{yf_period}_{interval}",
        granularity=ttl_granularity,
        download=lambda candidate: yf.download(
            candidate,
            period=yf_period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        ),
        include_time=interval.endswith("m"),
    )
    return _filter_period(df, period)


def fetch_prices(
    ticker: str,
    period: str = "6M",
    granularity: Granularity = "daily",
) -> pd.DataFrame:
    yf_period = _PERIOD_MAP.get(period, "6mo")
    return _fetch_with_fallback(
        ticker,
        cache_key=lambda candidate: f"{candidate}_{yf_period}_{granularity}",
        granularity=granularity,
        download=lambda candidate: yf.download(candidate, period=yf_period, auto_adjust=True, progress=False),
    )


def fetch_prices_for_strategy(ticker: str, years: int = 5) -> pd.DataFrame:
    return _fetch_with_fallback(
        ticker,
        cache_key=lambda candidate: f"{candidate}_{years}y",
        granularity="daily",
        download=lambda candidate: yf.download(candidate, period=f"{years}y", auto_adjust=True, progress=False),
    )


def fetch_quote(ticker: str) -> pd.DataFrame:
    return _fetch_with_fallback(
        ticker,
        cache_key=lambda candidate: f"{candidate}_quote",
        granularity="quote",
        download=lambda candidate: yf.download(
            candidate,
            period="1d",
            interval="1m",
            auto_adjust=True,
            progress=False,
        ),
    )


def _resolution_candidates(ticker: str) -> list[str]:
    candidates = normalize_ticker_with_fallback(ticker)
    resolved = get_resolved_ticker(ticker)
    if not resolved:
        return candidates
    resolved = resolved.upper()
    return [resolved] + [candidate for candidate in candidates if candidate != resolved]


def _fetch_with_fallback(
    ticker: str,
    cache_key: Callable[[str], str],
    granularity: Granularity,
    download: Callable[[str], pd.DataFrame],
    include_time: bool = False,
) -> pd.DataFrame:
    candidates = _resolution_candidates(ticker)
    for candidate in candidates:
        key = cache_key(candidate)
        cached = get_price_cache(
            key,
            ttl_override=cache_ttl_seconds(candidate, granularity),
        )
        if cached is not None and not cached.empty:
            return cached

    for candidate in candidates:
        try:
            raw = download(candidate)
            df = _normalize_df(raw, include_time=include_time)
            if not df.empty:
                save_price_cache(cache_key(candidate), df)
                save_ticker_resolution(ticker, candidate)
                return df
        except Exception:
            continue
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
