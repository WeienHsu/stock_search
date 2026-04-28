from datetime import datetime, timedelta

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.strategies.strategy_d import scan_strategy_d, scan_strategy_d_sell

_GREEN_DAYS = 3
_YELLOW_DAYS = 90


def scan_watchlist(items: list[dict], strategy_params: dict) -> pd.DataFrame:
    """
    Scan each ticker for Strategy D buy AND sell signal status.

    Returns DataFrame with columns:
        ticker, name, buy_signal, sell_signal,
        buy_status, sell_status, last_buy_date, last_sell_date, current_close
    """
    p = strategy_params
    rows = []
    today = datetime.today().date()

    for item in items:
        ticker = normalize_ticker(item["ticker"])
        name = item.get("name", "")

        try:
            df = fetch_prices_for_strategy(ticker, years=1)
            if df.empty:
                rows.append(_error_row(ticker, name, "無資料"))
                continue

            df = add_macd(df, fast=p.get("macd_fast", 12), slow=p.get("macd_slow", 26), signal=p.get("macd_signal", 9))
            df = add_kd(df, k=p.get("kd_k", 9), d=p.get("kd_d", 3), smooth_k=p.get("kd_smooth_k", 3))

            current_close = round(float(df["close"].iloc[-1]), 2)

            # ── Buy scan ──
            buy_df = scan_strategy_d(
                df,
                kd_window=p.get("kd_window", 10),
                n_bars=p.get("n_bars", 3),
                recovery_pct=p.get("recovery_pct", 0.7),
                kd_k_threshold=p.get("kd_k_threshold", 20),
            )
            buy_status, buy_active, last_buy_date = _classify_signal(buy_df, today, _GREEN_DAYS, _YELLOW_DAYS, "買進")

            # ── Sell scan ──
            sell_status = "⚪ 無訊號"
            sell_active = False
            last_sell_date = "—"
            if p.get("enable_sell_signal", True):
                sell_df = scan_strategy_d_sell(
                    df,
                    kd_window=p.get("kd_window", 10),
                    n_bars=p.get("n_bars", 3),
                    recovery_pct=p.get("recovery_pct", 0.7),
                    kd_d_threshold=p.get("kd_d_threshold", 80),
                )
                sell_status, sell_active, last_sell_date = _classify_signal(sell_df, today, _GREEN_DAYS, _YELLOW_DAYS, "賣出")

            rows.append({
                "ticker": ticker,
                "name": name,
                "signal": buy_active,          # kept for backward compat
                "buy_signal": buy_active,
                "sell_signal": sell_active,
                "last_signal_date": last_buy_date,   # kept for backward compat
                "last_buy_date": last_buy_date,
                "last_sell_date": last_sell_date,
                "current_close": current_close,
                "buy_status": buy_status,
                "sell_status": sell_status,
            })

        except Exception as e:
            rows.append(_error_row(ticker, name, str(e)[:40]))

    return pd.DataFrame(rows)


def _classify_signal(
    sig_df: pd.DataFrame,
    today: datetime,
    green_days: int,
    yellow_days: int,
    label: str,
) -> tuple[str, bool, str]:
    """Return (status_str, is_active_today, last_date_str)."""
    if sig_df.empty:
        return "⚪ 無訊號", False, "—"
    last_date_str = str(sig_df["date"].iloc[-1])[:10]
    last_dt = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    days_ago = (today - last_dt).days
    if days_ago <= green_days:
        return f"🟢 {label}觸發", True, last_date_str
    if days_ago <= yellow_days:
        return f"🟡 近期{label}", False, last_date_str
    return "⚪ 無訊號", False, last_date_str


def _error_row(ticker: str, name: str, err: str) -> dict:
    return {
        "ticker": ticker, "name": name,
        "signal": False, "buy_signal": False, "sell_signal": False,
        "last_signal_date": "—", "last_buy_date": "—", "last_sell_date": "—",
        "current_close": 0.0,
        "buy_status": f"❌ {err}", "sell_status": "—",
    }
