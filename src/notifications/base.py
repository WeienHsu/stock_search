from __future__ import annotations

from dataclasses import dataclass

from src.repositories.notification_settings_repo import channels_for


@dataclass
class NotificationResult:
    channel: str
    success: bool
    error: str = ""


def send_notification(
    user_id: str,
    subject: str,
    body: str,
    *,
    severity: str = "info",
    event_type: str = "price_alert",
) -> list[NotificationResult]:
    from src.notifications.email import EmailChannel
    from src.notifications.inbox import InboxChannel
    from src.notifications.telegram import TelegramChannel

    channel_map = {
        "email": EmailChannel(),
        "telegram": TelegramChannel(),
        "inbox": InboxChannel(),
    }
    requested = channels_for(user_id, event_type)
    results: list[NotificationResult] = []

    for name in requested:
        channel = channel_map.get(name)
        if channel is None:
            results.append(NotificationResult(name, False, "Unknown channel"))
            continue
        try:
            ok = channel.send(user_id, subject, body, severity=severity)
            results.append(NotificationResult(name, bool(ok)))
        except Exception as exc:
            results.append(NotificationResult(name, False, str(exc)))

    external_success = any(
        result.success and result.channel in {"email", "telegram"}
        for result in results
    )
    inbox_requested = any(result.channel == "inbox" for result in results)
    if not external_success and not inbox_requested:
        try:
            ok = InboxChannel().send(user_id, subject, body, severity=severity)
            results.append(NotificationResult("inbox", bool(ok)))
        except Exception as exc:
            results.append(NotificationResult("inbox", False, str(exc)))

    return results
