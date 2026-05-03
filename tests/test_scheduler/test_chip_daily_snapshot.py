from src.scheduler.jobs import chip_daily_snapshot


def test_chip_daily_snapshot_dedupes_tickers(monkeypatch):
    saved = []
    monkeypatch.setattr(chip_daily_snapshot, "list_users", lambda: [{"user_id": "u1"}, {"user_id": "u2"}])
    monkeypatch.setattr(
        chip_daily_snapshot,
        "get_watchlist",
        lambda user_id: [{"ticker": "2330.TW"}, {"ticker": "2317.TW"}] if user_id == "u1" else [{"ticker": "2330.TW"}],
    )
    monkeypatch.setattr(
        chip_daily_snapshot,
        "fetch_today",
        lambda ticker: {
            "supported": True,
            "ticker": ticker,
            "date": "2026-05-01",
            "institutional_foreign": 1.0,
            "institutional_trust": 0.5,
            "institutional_dealer": -0.2,
            "margin_balance": 12827,
            "short_balance": 43,
            "qfiis_pct": 72.34,
            "source": {"institutional": "chip_finmind"},
        },
    )
    monkeypatch.setattr(chip_daily_snapshot, "save_chip_snapshot", lambda snapshot: saved.append(snapshot["ticker"]))
    monkeypatch.setattr(chip_daily_snapshot, "start_run", lambda job_name: 1)
    monkeypatch.setattr(chip_daily_snapshot, "finish_run", lambda *args, **kwargs: None)

    result = chip_daily_snapshot.run_chip_daily_snapshot()

    assert result["tickers_written"] == 2
    assert saved == ["2317.TW", "2330.TW"]
