from __future__ import annotations

import json
from urllib.request import Request, urlopen

from src.repositories.notification_settings_repo import get_settings
from src.repositories.user_secrets_repo import get_secret


class TelegramChannel:
    def send(self, user_id: str, subject: str, body: str, *, severity: str = "info") -> bool:
        settings = get_settings(user_id)
        if not settings.get("telegram_enabled"):
            return False

        token = get_secret(user_id, "telegram_bot_token")
        chat_id = str(settings.get("telegram_chat_id") or "").strip()
        if not token or not chat_id:
            return False

        text = f"*{_escape_markdown(subject)}*\n{_escape_markdown(body)}"
        payload = json.dumps(
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        return bool(data.get("ok"))


def _escape_markdown(value: str) -> str:
    return "".join(f"\\{ch}" if ch in r"_*[]()~`>#+-=|{}.!" else ch for ch in value)
