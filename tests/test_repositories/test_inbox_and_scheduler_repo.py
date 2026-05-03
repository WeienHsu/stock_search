from src.repositories import inbox_repo, scheduler_run_repo


def test_inbox_message_lifecycle(tmp_path):
    db_path = tmp_path / "alerts.db"

    message = inbox_repo.add_message(
        "user-1",
        "Subject",
        "Body",
        severity="warning",
        db_path=db_path,
    )

    assert inbox_repo.unread_count("user-1", db_path=db_path) == 1
    messages = inbox_repo.list_messages("user-1", db_path=db_path)
    assert messages[0]["subject"] == "Subject"

    inbox_repo.mark_read(message["id"], db_path=db_path)
    assert inbox_repo.unread_count("user-1", db_path=db_path) == 0


def test_scheduler_run_lifecycle(tmp_path):
    db_path = tmp_path / "alerts.db"

    run_id = scheduler_run_repo.start_run("price_alerts", db_path=db_path)
    scheduler_run_repo.finish_run(run_id, "success", db_path=db_path)

    runs = scheduler_run_repo.list_runs(db_path=db_path)
    assert runs[0]["job_name"] == "price_alerts"
    assert runs[0]["status"] == "success"
