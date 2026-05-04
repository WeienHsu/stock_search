from pathlib import Path

from src.repositories import strategy_scan_events_repo as repo


def test_strategy_scan_event_upsert_and_filter(tmp_path: Path):
    db_path = tmp_path / "scan_events.db"

    repo.save_scan_event(
        "user-1",
        "tsla",
        "strategy_d",
        "buy",
        "2026-05-04",
        "triggered",
        {"buy_status": "triggered"},
        db_path=db_path,
    )
    repo.save_scan_event(
        "user-1",
        "TSLA",
        "strategy_d",
        "buy",
        "2026-05-04",
        "no_signal",
        {"buy_status": "updated"},
        db_path=db_path,
    )

    rows = repo.list_scan_events("user-1", since_date="2026-05-01", ticker="TSLA", db_path=db_path)

    assert len(rows) == 1
    assert rows[0]["ticker"] == "TSLA"
    assert rows[0]["status"] == "no_signal"
    assert rows[0]["payload"]["buy_status"] == "updated"
