from datetime import datetime, timedelta

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.strategies.strategy_d import scan_strategy_d


def run_backtest(
    ticker: str,
    strategy_params: dict,
    forward_days: int = 60,
    years: int = 1,
) -> pd.DataFrame:
    """
    Scan all Strategy D signals in the past `years` and compute forward returns.

    Returns DataFrame with columns:
        date, signal_close, forward_close, forward_return_pct, win
    """
    ticker = normalize_ticker(ticker)
    df = fetch_prices_for_strategy(ticker, years=years)
    if df.empty:
        return pd.DataFrame()

    p = strategy_params
    df = add_macd(df, fast=p.get("macd_fast", 12), slow=p.get("macd_slow", 26), signal=p.get("macd_signal", 9))
    df = add_kd(df, k=p.get("kd_k", 9), d=p.get("kd_d", 3), smooth_k=p.get("kd_smooth_k", 3))

    sig_df = scan_strategy_d(
        df,
        kd_window=p.get("kd_window", 10),
        n_bars=p.get("n_bars", 3),
        recovery_pct=p.get("recovery_pct", 0.7),
        kd_k_threshold=p.get("kd_k_threshold", 20),
    )

    if sig_df.empty:
        return pd.DataFrame()

    date_to_close = dict(zip(df["date"], df["close"]))
    all_dates = sorted(date_to_close.keys())

    rows = []
    for _, row in sig_df.iterrows():
        sig_date = str(row["date"])[:10]
        sig_close = float(row["close"])

        # Find the close price ~forward_days trading days later
        try:
            sig_idx = all_dates.index(sig_date)
        except ValueError:
            continue
        fwd_idx = min(sig_idx + forward_days, len(all_dates) - 1)
        fwd_date = all_dates[fwd_idx]
        fwd_close = date_to_close[fwd_date]

        fwd_return = (fwd_close - sig_close) / sig_close * 100

        rows.append({
            "date": sig_date,
            "forward_date": fwd_date,
            "signal_close": round(sig_close, 4),
            "forward_close": round(fwd_close, 4),
            "forward_return_pct": round(fwd_return, 2),
            "win": fwd_return > 0,
        })

    return pd.DataFrame(rows)
