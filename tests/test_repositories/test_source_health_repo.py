from src.repositories.source_health_repo import format_health_summary, get_source_health, record_source_health


def test_source_health_repo_records_success_and_failure(tmp_path):
    db_path = tmp_path / "source_health.db"

    record_source_health("chip_finmind", "ok", db_path=db_path)
    record_source_health("chip_finmind", "unavailable", reason="throttled", db_path=db_path)

    health = get_source_health("chip_finmind", db_path=db_path)

    assert health["last_status"] == "unavailable"
    assert health["last_error"] == "throttled"
    assert "最後成功" in format_health_summary(health)
