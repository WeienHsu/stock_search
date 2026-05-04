from __future__ import annotations

import json
from typing import Any

import pandas as pd

import src.strategies.strategy_d  # ensure registration
import src.strategies.strategy_kd  # ensure registration

from src.auth.auth_manager import list_users
from src.core.strategy_registry import list_strategies
from src.notifications import send_notification
from src.repositories.scheduler_run_repo import finish_run, start_run
from src.repositories.strategy_scan_events_repo import save_scan_event
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
            _record_scan_events(user["user_id"], strategy_id, result)
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


def _record_scan_events(user_id: str, strategy_id: str, result: pd.DataFrame) -> None:
    for row in result.to_dict("records"):
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        payload = {key: _json_safe(value) for key, value in row.items()}
        is_error = str(row.get("buy_status") or "").startswith("❌")
        for signal_type in ("buy", "sell"):
            date_key = f"last_{signal_type}_date"
            signal_key = f"{signal_type}_signal"
            event_date = str(row.get(date_key) or "")[:10]
            if not event_date or event_date == "—":
                event_date = str(pd.Timestamp.today().date())
            if is_error:
                status = "error"
            elif bool(row.get(signal_key)):
                status = "triggered"
            else:
                status = "no_signal"
            save_scan_event(
                user_id,
                ticker,
                strategy_id,
                signal_type,
                event_date,
                status,
                payload,
            )


def _json_safe(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    print(json.dumps(run_daily_scan(), ensure_ascii=False, default=str))
