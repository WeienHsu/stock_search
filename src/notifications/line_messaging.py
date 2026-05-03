from __future__ import annotations

import json
from urllib.request import Request, urlopen

from src.repositories.notification_settings_repo import get_settings
from src.repositories.user_secrets_repo import get_secret


class LineMessagingChannel:
    """LINE Official Account Messaging API push-message channel."""

    def send(self, user_id: str, subject: str, body: str, *, severity: str = "info") -> bool:
        settings = get_settings(user_id)
        if not settings.get("line_enabled"):
            return False

        target_id = str(settings.get("line_user_id") or "").strip()
        token = get_secret(user_id, "line_channel_access_token")
        if not target_id or not token:
            return False

        payload = json.dumps({
            "to": target_id,
            "messages": [{"type": "text", "text": _line_text(subject, body)}],
        }).encode("utf-8")
        request = Request(
            "https://api.line.me/v2/bot/message/push",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            return 200 <= int(getattr(response, "status", 200)) < 300


def _line_text(subject: str, body: str) -> str:
    text = f"{subject}\n\n{body}".strip()
    return text[:5000]
