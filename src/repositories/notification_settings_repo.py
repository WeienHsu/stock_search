from __future__ import annotations

from typing import Any

from src.repositories._backends import get_user_backend

_backend = get_user_backend()
_KEY = "notification_settings"

DEFAULT_SETTINGS: dict[str, Any] = {
    "email_enabled": False,
    "email_to": "",
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_use_tls": True,
    "telegram_enabled": False,
    "telegram_chat_id": "",
    "line_enabled": False,
    "line_user_id": "",
    "inbox_enabled": True,
    "price_alert_channels": ["inbox"],
    "strategy_alert_channels": ["inbox"],
    "weekly_digest_channels": ["inbox"],
    "daily_digest_channels": ["inbox"],
}


def get_settings(user_id: str) -> dict[str, Any]:
    saved = _backend.get(user_id, _KEY, default={}) or {}
    return {**DEFAULT_SETTINGS, **saved}


def save_settings(user_id: str, settings: dict[str, Any]) -> None:
    merged = {**DEFAULT_SETTINGS, **settings}
    _backend.save(user_id, _KEY, merged)


def channels_for(user_id: str, event_type: str) -> list[str]:
    settings = get_settings(user_id)
    key = {
        "price_alert": "price_alert_channels",
        "strategy_alert": "strategy_alert_channels",
        "weekly_digest": "weekly_digest_channels",
        "daily_digest": "daily_digest_channels",
    }.get(event_type, "price_alert_channels")
    channels = settings.get(key) or ["inbox"]
    enabled = []
    for channel in channels:
        if channel == "email" and settings.get("email_enabled"):
            enabled.append(channel)
        elif channel == "telegram" and settings.get("telegram_enabled"):
            enabled.append(channel)
        elif channel == "line" and settings.get("line_enabled"):
            enabled.append(channel)
        elif channel == "inbox" and settings.get("inbox_enabled", True):
            enabled.append(channel)
    return enabled or ["inbox"]
