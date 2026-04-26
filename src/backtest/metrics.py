import numpy as np
import pandas as pd


def compute_metrics(bt_df: pd.DataFrame, forward_days: int = 60) -> dict:
    """
    Compute backtest performance metrics from a backtest DataFrame.

    Expected columns: forward_return_pct, win
    Returns dict with: count, win_rate, total_return_pct, mean_return_pct,
                        median_return_pct, max_drawdown_pct, sharpe
    """
    if bt_df.empty:
        return {
            "count": 0, "win_rate": 0.0, "total_return_pct": 0.0,
            "mean_return_pct": 0.0, "median_return_pct": 0.0,
            "max_drawdown_pct": 0.0, "sharpe": 0.0,
        }

    returns = bt_df["forward_return_pct"].values
    n = len(returns)

    win_rate = float(bt_df["win"].mean()) * 100
    mean_ret = float(np.mean(returns))
    median_ret = float(np.median(returns))

    # Compounded total return across all signals (equal-weight, non-overlapping assumption)
    total_return = float(np.prod(1 + returns / 100) - 1) * 100

    # MDD on equity curve (cumulative product of (1 + r))
    equity = np.cumprod(1 + returns / 100)
    roll_max = np.maximum.accumulate(equity)
    drawdowns = (equity - roll_max) / roll_max * 100
    max_drawdown = float(drawdowns.min())

    # Annualised Sharpe (risk-free = 0, periods_per_year = 252 / forward_days)
    std = float(np.std(returns, ddof=1)) if n > 1 else 0.0
    periods_per_year = 252 / forward_days
    sharpe = (mean_ret / std * np.sqrt(periods_per_year)) if std > 0 else 0.0

    return {
        "count": n,
        "win_rate": round(win_rate, 1),
        "total_return_pct": round(total_return, 2),
        "mean_return_pct": round(mean_ret, 2),
        "median_return_pct": round(median_ret, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe": round(sharpe, 2),
    }
