from src.repositories import alert_repo


def test_create_list_and_trigger_price_alert(tmp_path):
    db_path = tmp_path / "alerts.db"

    alert = alert_repo.create_price_alert(
        "user-1",
        "tsla",
        "above",
        250,
        db_path=db_path,
    )

    alerts = alert_repo.list_alerts("user-1", db_path=db_path)
    active = alert_repo.list_active_alerts(db_path=db_path)

    assert alerts[0]["ticker"] == "TSLA"
    assert active[0]["id"] == alert["id"]
    assert alert_repo.alert_is_triggered(active[0], 251)
    assert not alert_repo.alert_is_triggered(active[0], 249)

    alert_repo.mark_triggered(
        alert["id"],
        event_type="price_alert_triggered",
        payload={"current_price": 251},
        delivered_at=123,
        db_path=db_path,
    )

    assert alert_repo.list_active_alerts(db_path=db_path) == []
    events = alert_repo.list_events("user-1", db_path=db_path)
    assert events[0]["payload"] == {"current_price": 251}


def test_disable_and_delete_alert(tmp_path):
    db_path = tmp_path / "alerts.db"
    alert = alert_repo.create_price_alert("user-1", "TSLA", "below", 200, db_path=db_path)

    alert_repo.set_alert_enabled(alert["id"], False, db_path=db_path)
    assert alert_repo.list_active_alerts(db_path=db_path) == []

    alert_repo.delete_alert(alert["id"], db_path=db_path)
    assert alert_repo.list_alerts("user-1", db_path=db_path) == []
