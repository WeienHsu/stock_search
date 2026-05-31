import pandas as pd

from src.scheduler.jobs import daily_scan


def test_record_scan_events_writes_buy_and_sell(monkeypatch):
    saved = []
    monkeypatch.setattr(
        daily_scan,
        "save_scan_event",
        lambda *args, **kwargs: saved.append(args),
    )
    result = pd.DataFrame([
        {
            "ticker": "TSLA",
            "buy_signal": True,
            "sell_signal": False,
            "last_buy_date": "2026-05-04",
            "last_sell_date": "—",
            "buy_status": "▲ 買進觸發",
            "sell_status": "⚪ 無訊號",
            "current_close": 100.0,
        }
    ])

    daily_scan._record_scan_events("user-1", "strategy_d", result)

    assert len(saved) == 2
    assert saved[0][:6] == ("user-1", "TSLA", "strategy_d", "buy", "2026-05-04", "triggered")
    assert saved[1][3] == "sell"
    assert saved[1][5] == "no_signal"


def test_run_daily_scan_skips_non_trading_day(monkeypatch):
    monkeypatch.setattr(daily_scan, "is_trading_day", lambda ticker: False)
    monkeypatch.setattr(daily_scan, "list_users", lambda: (_ for _ in ()).throw(AssertionError("no users")))
    monkeypatch.setattr(daily_scan, "scan_watchlist", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no scan")))
    monkeypatch.setattr(daily_scan, "start_run", lambda job_name: 1)
    monkeypatch.setattr(daily_scan, "finish_run", lambda *args, **kwargs: None)

    result = daily_scan.run_daily_scan()

    assert result["skipped"] is True
    assert result["skipped_reason"] == "non_trading_day"
    assert result["notifications_sent"] == 0
