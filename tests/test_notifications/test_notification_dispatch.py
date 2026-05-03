from src.notifications import base
from src.notifications.email import EmailChannel
from src.notifications.inbox import InboxChannel
from src.notifications.telegram import TelegramChannel


def test_send_notification_falls_back_to_inbox(monkeypatch):
    sent = []

    monkeypatch.setattr(base, "channels_for", lambda user_id, event_type: ["email", "telegram"])
    monkeypatch.setattr(EmailChannel, "send", lambda self, *args, **kwargs: False)
    monkeypatch.setattr(TelegramChannel, "send", lambda self, *args, **kwargs: False)
    monkeypatch.setattr(
        InboxChannel,
        "send",
        lambda self, user_id, subject, body, severity="info": sent.append(
            (user_id, subject, body, severity)
        )
        or True,
    )

    results = base.send_notification("user-1", "Subject", "Body", severity="warning")

    assert [result.channel for result in results] == ["email", "telegram", "inbox"]
    assert results[-1].success
    assert sent == [("user-1", "Subject", "Body", "warning")]


def test_send_notification_does_not_duplicate_requested_inbox(monkeypatch):
    sent = []

    monkeypatch.setattr(base, "channels_for", lambda user_id, event_type: ["inbox"])
    monkeypatch.setattr(
        InboxChannel,
        "send",
        lambda self, user_id, subject, body, severity="info": sent.append(subject) or True,
    )

    results = base.send_notification("user-1", "Subject", "Body")

    assert [result.channel for result in results] == ["inbox"]
    assert sent == ["Subject"]
