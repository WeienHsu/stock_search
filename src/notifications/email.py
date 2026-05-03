from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.repositories.notification_settings_repo import get_settings
from src.repositories.user_secrets_repo import get_secret


class EmailChannel:
    def send(self, user_id: str, subject: str, body: str, *, severity: str = "info") -> bool:
        settings = get_settings(user_id)
        if not settings.get("email_enabled"):
            return False

        host = str(settings.get("smtp_host") or "").strip()
        username = str(settings.get("smtp_username") or "").strip()
        recipient = str(settings.get("email_to") or username).strip()
        password = get_secret(user_id, "smtp_password")
        if not host or not username or not recipient or not password:
            return False
        password = _normalize_smtp_password(host, password)

        port = int(settings.get("smtp_port") or 587)
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = username
        message["To"] = recipient
        message.attach(MIMEText(body, "plain", "utf-8"))
        message.attach(MIMEText(_html_body(subject, body, severity), "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if settings.get("smtp_use_tls", True):
                smtp.starttls()
            smtp.login(username, password)
            smtp.sendmail(username, [recipient], message.as_string())
        return True


def _normalize_smtp_password(host: str, password: str) -> str:
    """Gmail app passwords are displayed in groups; SMTP expects the raw token."""
    if "gmail" in host.lower():
        return "".join(password.split())
    return password.strip()


def _html_body(subject: str, body: str, severity: str) -> str:
    accent = {
        "info": "#3d7f88",
        "warning": "#b7791f",
        "error": "#c53030",
        "success": "#2f855a",
    }.get(severity, "#3d7f88")
    escaped_body = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <html>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #243235;">
        <div style="border-left: 4px solid {accent}; padding: 12px 16px;">
          <h2 style="margin: 0 0 12px;">{subject}</h2>
          <pre style="white-space: pre-wrap; font-family: inherit; line-height: 1.5;">{escaped_body}</pre>
        </div>
      </body>
    </html>
    """
