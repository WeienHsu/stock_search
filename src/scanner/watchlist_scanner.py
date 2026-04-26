from datetime import datetime, timedelta

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd
from src.strategies.strategy_d import scan_strategy_d

# ── 狀態判定閾值 ──
_GREEN_DAYS = 3       # 三日內有訊號 → 🟢
_YELLOW_DAYS = 90     # 三個月內有訊號 → 🟡


def scan_watchlist(items: list[dict], strategy_params: dict) -> pd.DataFrame:
    """
    Scan each ticker in the watchlist for Strategy D signal status.

    Status rules:
        🟢 訊號觸發：三日內 Strategy D 成立
        🟡 近期有訊號：過去 3 個月內有訊號
        ⚪ 無訊號：超過 3 個月或從未觸發
        ❌ 錯誤：資料取得失敗

    Returns DataFrame with columns:
        ticker, name, signal, last_signal_date, current_close, status
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

            sig_df = scan_strategy_d(
                df,
                kd_window=p.get("kd_window", 10),
                n_bars=p.get("n_bars", 3),
                recovery_pct=p.get("recovery_pct", 0.7),
                kd_k_threshold=p.get("kd_k_threshold", 20),
            )

            current_close = round(float(df["close"].iloc[-1]), 2)

            if sig_df.empty:
                last_signal_date = "—"
                status = "⚪ 無訊號"
                is_active = False
            else:
                last_signal_date = str(sig_df["date"].iloc[-1])[:10]
                last_dt = datetime.strptime(last_signal_date, "%Y-%m-%d").date()
                days_ago = (today - last_dt).days

                if days_ago <= _GREEN_DAYS:
                    status = "🟢 訊號觸發"
                    is_active = True
                elif days_ago <= _YELLOW_DAYS:
                    status = "🟡 近期有訊號"
                    is_active = False
                else:
                    status = "⚪ 無訊號"
                    is_active = False

            rows.append({
                "ticker": ticker,
                "name": name,
                "signal": is_active,
                "last_signal_date": last_signal_date,
                "current_close": current_close,
                "status": status,
            })

        except Exception as e:
            rows.append(_error_row(ticker, name, str(e)[:40]))

    return pd.DataFrame(rows)


def _error_row(ticker: str, name: str, err: str) -> dict:
    return {
        "ticker": ticker, "name": name,
        "signal": False, "last_signal_date": "—",
        "current_close": 0.0, "status": f"❌ {err}",
    }
