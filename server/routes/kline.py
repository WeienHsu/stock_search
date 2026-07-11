import math
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.core.strategy_registry import get as get_strategy, list_strategies
from src.data.price_fetcher import fetch_prices_by_interval
from src.data.ticker_utils import normalize_ticker
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.macd import add_macd

router = APIRouter(tags=["kline"])

_MA_PERIODS = [5, 10, 20, 60]
_PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1095, "5Y": 1825}


@router.get("/strategies")
def strategies() -> list[dict]:
    return [
        {"id": sid, "default_params": get_strategy(sid).default_params()}
        for sid in list_strategies()
    ]


@router.get("/kline/{symbol}")
def kline(
    symbol: str,
    interval: str = "1d",
    period: str = "1Y",
    strategy_id: str = "strategy_d",
    enable_early: bool = False,
) -> dict:
    ticker = normalize_ticker(symbol)
    df = fetch_prices_by_interval(ticker, interval, period)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    df = add_ma(df, _MA_PERIODS)
    try:
        df = add_kd(df)
    except ValueError:
        pass
    try:
        df = add_macd(df)
    except ValueError:
        pass

    signals: list[dict] = []
    if interval == "1d":
        try:
            strategy = get_strategy(strategy_id)
            params = {**strategy.default_params(), "enable_early_signal": enable_early}
            raw = strategy.compute(df, params)
            signals = [
                {"date": s.date[:10], "type": s.signal_type, "strength": s.strength, "tier": s.tier}
                for s in raw
            ]
        except Exception:
            signals = []

    if interval == "1d":
        days = _PERIOD_DAYS.get(period)
        if days:
            dates = pd.to_datetime(df["date"], errors="coerce")
            cutoff = dates.max() - pd.Timedelta(days=days)
            df = df[dates >= cutoff].reset_index(drop=True)
            signals = [s for s in signals if s["date"] >= str(cutoff.date())]

    candles = [
        {
            "time": row["date"],
            "open": _f(row["open"]),
            "high": _f(row["high"]),
            "low": _f(row["low"]),
            "close": _f(row["close"]),
            "volume": _f(row.get("volume")),
        }
        for row in df.to_dict("records")
    ]
    return {
        "symbol": ticker,
        "interval": interval,
        "candles": candles,
        "indicators": {
            "ma": {str(p): _col(df, f"MA_{p}") for p in _MA_PERIODS},
            "kd": {"k": _col(df, "K"), "d": _col(df, "D")},
            "macd": {
                "macd": _col(df, "macd_line"),
                "signal": _col(df, "signal_line"),
                "hist": _col(df, "histogram"),
            },
        },
        "signals": signals,
    }


def _f(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _col(df: pd.DataFrame, name: str) -> list[float | None]:
    if name not in df.columns:
        return []
    return [_f(v) for v in df[name]]
