import json

from src.notifications import base
from src.notifications.email import EmailChannel
from src.notifications.inbox import InboxChannel
from src.notifications.line_messaging import LineMessagingChannel
from src.notifications.telegram import TelegramChannel


def test_send_notification_dry_run_records_without_sending(monkeypatch, tmp_path):
    output = tmp_path / "dry_run_notifications.jsonl"
    monkeypatch.setenv("NOTIFICATION_DRY_RUN", "1")
    monkeypatch.setenv("NOTIFICATION_DRY_RUN_PATH", str(output))
    monkeypatch.setattr(base, "channels_for", lambda user_id, event_type: ["email", "telegram", "line", "inbox"])

    def fail_send(self, *args, **kwargs):
        raise AssertionError("real channel send should not be called in dry-run")

    monkeypatch.setattr(EmailChannel, "send", fail_send)
    monkeypatch.setattr(TelegramChannel, "send", fail_send)
    monkeypatch.setattr(LineMessagingChannel, "send", fail_send)
    monkeypatch.setattr(InboxChannel, "send", fail_send)

    results = base.send_notification(
        "user-1",
        "Subject",
        "Body",
        severity="warning",
        event_type="weekly_digest",
    )

    assert [result.channel for result in results] == ["email", "telegram", "line", "inbox"]
    assert all(result.success for result in results)
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [record["channel"] for record in records] == ["email", "telegram", "line", "inbox"]
    assert {record["event_type"] for record in records} == {"weekly_digest"}
