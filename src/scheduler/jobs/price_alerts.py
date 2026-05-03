from __future__ import annotations

import time
from typing import Any

from src.data.price_fetcher import fetch_quote
from src.notifications import send_notification
from src.repositories import alert_repo
from src.repositories.scheduler_run_repo import finish_run, start_run

JOB_NAME = "price_alerts"


def run_price_alerts() -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    checked = 0
    triggered = 0
    try:
        for alert in alert_repo.list_active_alerts():
            if alert["type"] != "price":
                continue
            checked += 1
            df = fetch_quote(alert["ticker"])
            if df.empty or "close" not in df.columns:
                continue
            current_price = float(df["close"].iloc[-1])
            if not alert_repo.alert_is_triggered(alert, current_price):
                continue

            subject = f"{alert['ticker']} 價格警示觸發"
            comparator = ">=" if alert["direction"] == "above" else "<="
            body = (
                f"{alert['ticker']} 現價 {current_price:.2f} "
                f"{comparator} {float(alert['threshold']):.2f}\n"
                f"Alert ID: {alert['id']}"
            )
            results = send_notification(
                alert["user_id"],
                subject,
                body,
                severity="warning",
                event_type="price_alert",
            )
            delivered = any(result.success for result in results)
            alert_repo.mark_triggered(
                alert["id"],
                event_type="price_alert_triggered",
                payload={
                    "current_price": current_price,
                    "threshold": alert["threshold"],
                    "direction": alert["direction"],
                    "notification_results": [result.__dict__ for result in results],
                },
                delivered_at=time.time() if delivered else None,
            )
            triggered += 1
        finish_run(run_id, "success")
        return {"checked": checked, "triggered": triggered}
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise
