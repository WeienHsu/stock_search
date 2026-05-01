from datetime import datetime

import pandas as pd

from src.core.strategy_registry import get as get_strategy
from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker

_GREEN_DAYS = 3
_YELLOW_DAYS = 90


def scan_watchlist(
    items: list[dict],
    strategy_id: str,
    strategy_params: dict,
) -> pd.DataFrame:
    """Scan each ticker for buy AND sell signal status using any registered strategy.

    Returns DataFrame with columns:
        ticker, name, buy_signal, sell_signal,
        buy_status, sell_status, last_buy_date, last_sell_date, current_close
    """
    strategy = get_strategy(strategy_id)
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

            current_close = round(float(df["close"].iloc[-1]), 2)
            signals = strategy.compute(df, strategy_params)

            buy_signals = [s for s in signals if s.signal_type == "buy"]
            sell_signals = [s for s in signals if s.signal_type == "sell"]

            buy_status, buy_active, last_buy_date = _classify_signals(
                buy_signals, today, _GREEN_DAYS, _YELLOW_DAYS, "買進"
            )
            sell_status, sell_active, last_sell_date = _classify_signals(
                sell_signals, today, _GREEN_DAYS, _YELLOW_DAYS, "賣出"
            )

            rows.append({
                "ticker": ticker,
                "name": name,
                "signal": buy_active,
                "buy_signal": buy_active,
                "sell_signal": sell_active,
                "last_signal_date": last_buy_date,
                "last_buy_date": last_buy_date,
                "last_sell_date": last_sell_date,
                "current_close": current_close,
                "buy_status": buy_status,
                "sell_status": sell_status,
            })

        except Exception as e:
            rows.append(_error_row(ticker, name, str(e)[:40]))

    return pd.DataFrame(rows)


def _classify_signals(
    signals: list,
    today: datetime,
    green_days: int,
    yellow_days: int,
    label: str,
) -> tuple[str, bool, str]:
    """Return (status_str, is_active_today, last_date_str)."""
    if not signals:
        return "⚪ 無訊號", False, "—"
    last_date_str = max(s.date for s in signals)[:10]
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
