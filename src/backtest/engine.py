import pandas as pd

from src.core.strategy_registry import get as get_strategy
from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker


def run_backtest(
    ticker: str,
    strategy_id: str,
    strategy_params: dict,
    forward_days: int = 60,
    years: int = 1,
    signal_type: str = "buy",
) -> pd.DataFrame:
    """Backtest any registered strategy on historical data.

    Scans all signals of `signal_type` in the past `years` and computes
    forward returns (buy) or forward declines (sell).

    Returns DataFrame with columns:
        date, signal_close, forward_date, forward_close, forward_return_pct, win
    For sell signals "win" means price fell (forward_return_pct < 0).
    """
    ticker = normalize_ticker(ticker)
    df = fetch_prices_for_strategy(ticker, years=years)
    if df.empty:
        return pd.DataFrame()

    strategy = get_strategy(strategy_id)
    all_signals = strategy.compute(df, strategy_params)
    filtered = [s for s in all_signals if s.signal_type == signal_type]
    if not filtered:
        return pd.DataFrame()

    date_to_close = dict(zip(df["date"], df["close"]))
    all_dates = sorted(date_to_close.keys())

    rows = []
    for sig in filtered:
        sig_date = sig.date[:10]
        if sig_date not in date_to_close:
            continue
        sig_close = float(date_to_close[sig_date])
        try:
            sig_idx = all_dates.index(sig_date)
        except ValueError:
            continue
        fwd_idx = min(sig_idx + forward_days, len(all_dates) - 1)
        fwd_date = all_dates[fwd_idx]
        fwd_close = float(date_to_close[fwd_date])
        fwd_return = (fwd_close - sig_close) / sig_close * 100
        rows.append({
            "date": sig_date,
            "forward_date": fwd_date,
            "signal_close": round(sig_close, 4),
            "forward_close": round(fwd_close, 4),
            "forward_return_pct": round(fwd_return, 2),
            "win": (fwd_return < 0) if signal_type == "sell" else (fwd_return > 0),
        })

    return pd.DataFrame(rows)
