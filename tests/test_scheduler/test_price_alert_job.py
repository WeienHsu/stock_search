import pandas as pd

from src.scheduler.jobs import price_alerts


def test_run_price_alerts_triggers_matching_alert(monkeypatch):
    marked = []
    finished = []
    alert = {
        "id": "alert-1",
        "user_id": "user-1",
        "ticker": "TSLA",
        "type": "price",
        "direction": "above",
        "threshold": 250.0,
    }

    monkeypatch.setattr(price_alerts, "start_run", lambda job_name: 1)
    monkeypatch.setattr(
        price_alerts,
        "finish_run",
        lambda run_id, status, error=None: finished.append((run_id, status, error)),
    )
    monkeypatch.setattr(price_alerts.alert_repo, "list_active_alerts", lambda: [alert])
    monkeypatch.setattr(
        price_alerts,
        "fetch_quote",
        lambda ticker: pd.DataFrame({"close": [251.5]}),
    )
    monkeypatch.setattr(price_alerts.alert_repo, "alert_is_triggered", lambda alert, price: True)
    monkeypatch.setattr(
        price_alerts,
        "send_notification",
        lambda *args, **kwargs: [type("Result", (), {"success": True, "__dict__": {"success": True}})()],
    )
    monkeypatch.setattr(
        price_alerts.alert_repo,
        "mark_triggered",
        lambda *args, **kwargs: marked.append((args, kwargs)),
    )

    result = price_alerts.run_price_alerts()

    assert result == {"checked": 1, "triggered": 1}
    assert marked
    assert finished == [(1, "success", None)]
