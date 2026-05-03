from src.repositories.chip_snapshot_repo import get_latest_snapshot, list_recent_snapshots, save_chip_snapshot


def test_chip_snapshot_repo_saves_and_reads_latest(tmp_path):
    db_path = tmp_path / "chip_snapshots.db"
    save_chip_snapshot(
        {
            "ticker": "2330.TW",
            "date": "2026-05-01",
            "institutional_foreign": 1.5,
            "institutional_trust": 0.5,
            "institutional_dealer": -0.2,
            "margin_balance": 12827,
            "short_balance": 43,
            "qfiis_pct": 72.34,
            "source": {"institutional": "chip_finmind"},
        },
        db_path=db_path,
    )

    latest = get_latest_snapshot("2330.TW", db_path=db_path)
    rows = list_recent_snapshots("2330.TW", db_path=db_path)

    assert latest is not None
    assert latest["ticker"] == "2330.TW"
    assert latest["qfiis_pct"] == 72.34
    assert rows[0]["date"] == "2026-05-01"
