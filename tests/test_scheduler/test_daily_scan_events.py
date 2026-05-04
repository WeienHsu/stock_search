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
            "buy_status": "🟢 買進觸發",
            "sell_status": "⚪ 無訊號",
            "current_close": 100.0,
        }
    ])

    daily_scan._record_scan_events("user-1", "strategy_d", result)

    assert len(saved) == 2
    assert saved[0][:6] == ("user-1", "TSLA", "strategy_d", "buy", "2026-05-04", "triggered")
    assert saved[1][3] == "sell"
    assert saved[1][5] == "no_signal"
