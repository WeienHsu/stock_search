from __future__ import annotations

from typing import Any

from src.auth.auth_manager import list_users
from src.core.market_calendar import is_trading_day
from src.data.chip_fetcher import fetch_today
from src.repositories.chip_snapshot_repo import save_chip_snapshot
from src.repositories.scheduler_run_repo import finish_run, start_run
from src.repositories.watchlist_repo import get_watchlist

JOB_NAME = "chip_daily_snapshot"


def run_chip_daily_snapshot() -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    users_checked = 0
    tickers_written = 0
    seen: set[str] = set()
    try:
        if not is_trading_day("2330.TW"):
            finish_run(run_id, "success")
            return {
                "skipped": True,
                "skipped_reason": "non_trading_day",
                "users_checked": users_checked,
                "tickers_written": tickers_written,
            }

        for user in list_users():
            users_checked += 1
            for item in get_watchlist(user["user_id"]):
                ticker = str(item.get("ticker") or "").strip().upper()
                if ticker:
                    seen.add(ticker)

        for ticker in sorted(seen):
            snapshot = fetch_today(ticker)
            if not snapshot.get("supported"):
                continue
            save_chip_snapshot(snapshot)
            tickers_written += 1

        finish_run(run_id, "success")
        return {"users_checked": users_checked, "tickers_written": tickers_written}
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise
