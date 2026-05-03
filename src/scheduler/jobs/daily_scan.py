from __future__ import annotations

from typing import Any

import src.strategies.strategy_d  # ensure registration
import src.strategies.strategy_kd  # ensure registration

from src.auth.auth_manager import list_users
from src.core.strategy_registry import list_strategies
from src.notifications import send_notification
from src.repositories.scheduler_run_repo import finish_run, start_run
from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist

JOB_NAME = "daily_scan"


def run_daily_scan() -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    users_checked = 0
    notifications_sent = 0
    try:
        strategies = list_strategies()
        strategy_id = strategies[0] if strategies else "strategy_d"
        for user in list_users():
            users_checked += 1
            items = get_watchlist(user["user_id"])
            if not items:
                continue
            result = scan_watchlist(items, strategy_id=strategy_id, strategy_params={})
            if result.empty:
                continue
            triggered = result[(result["buy_signal"] == True) | (result["sell_signal"] == True)]
            if triggered.empty:
                continue
            lines = [
                f"{row.ticker}: 買進 {row.buy_status} / 賣出 {row.sell_status}"
                for row in triggered.itertuples()
            ]
            send_notification(
                user["user_id"],
                "每日策略掃描觸發",
                "\n".join(lines),
                severity="info",
                event_type="strategy_alert",
            )
            notifications_sent += 1
        finish_run(run_id, "success")
        return {"users_checked": users_checked, "notifications_sent": notifications_sent}
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise
