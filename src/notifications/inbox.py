from __future__ import annotations

from src.repositories.inbox_repo import add_message


class InboxChannel:
    def send(self, user_id: str, subject: str, body: str, *, severity: str = "info") -> bool:
        add_message(user_id, subject, body, severity=severity)
        return True
