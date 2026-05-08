from __future__ import annotations

import streamlit as st

from src.notifications import send_notification
from src.repositories.notification_settings_repo import get_settings, save_settings
from src.repositories.user_secrets_repo import set_secret


def render_notifications_section(user_id: str) -> None:
    st.markdown("### 通知設定")
    settings = get_settings(user_id)

    st.markdown("#### Email")
    email_enabled = st.checkbox("啟用 Email", value=bool(settings.get("email_enabled")), key="notify_email_enabled")
    col_email_to, col_smtp_host = st.columns(2)
    email_to = col_email_to.text_input("收件 Email", value=str(settings.get("email_to") or ""), key="notify_email_to")
    smtp_host = col_smtp_host.text_input("SMTP host", value=str(settings.get("smtp_host") or ""), key="notify_smtp_host")
    col_smtp_user, col_smtp_port, col_tls = st.columns([2, 1, 1])
    smtp_username = col_smtp_user.text_input("SMTP username", value=str(settings.get("smtp_username") or ""), key="notify_smtp_username")
    smtp_port = col_smtp_port.number_input("SMTP port", min_value=1, max_value=65535, value=int(settings.get("smtp_port") or 587), key="notify_smtp_port")
    smtp_use_tls = col_tls.checkbox("TLS", value=bool(settings.get("smtp_use_tls", True)), key="notify_smtp_tls")
    smtp_password = st.text_input("SMTP password / app password（留空表示不更換）", type="password", key="notify_smtp_password")

    st.markdown("#### Telegram")
    telegram_enabled = st.checkbox("啟用 Telegram", value=bool(settings.get("telegram_enabled")), key="notify_telegram_enabled")
    col_chat, col_token = st.columns(2)
    telegram_chat_id = col_chat.text_input("Telegram chat_id", value=str(settings.get("telegram_chat_id") or ""), key="notify_telegram_chat")
    telegram_token = col_token.text_input("Telegram bot token（留空表示不更換）", type="password", key="notify_telegram_token")

    st.markdown("#### LINE Messaging API")
    line_enabled = st.checkbox("啟用 LINE Messaging API", value=bool(settings.get("line_enabled")), key="notify_line_enabled")
    col_line_target, col_line_token = st.columns(2)
    line_user_id = col_line_target.text_input("LINE user_id / group_id", value=str(settings.get("line_user_id") or ""), key="notify_line_user")
    line_token = col_line_token.text_input("Channel access token（留空表示不更換）", type="password", key="notify_line_token")
    st.caption("LINE Notify 已終止；此處使用 LINE Official Account Messaging API push message。")

    st.markdown("#### 通道對映")
    channel_options = ["inbox", "email", "telegram", "line"]
    price_channels = st.multiselect("價格警示通道", channel_options, default=[c for c in settings.get("price_alert_channels", ["inbox"]) if c in channel_options], key="notify_price_channels")
    strategy_channels = st.multiselect("策略掃描通道", channel_options, default=[c for c in settings.get("strategy_alert_channels", ["inbox"]) if c in channel_options], key="notify_strategy_channels")
    weekly_channels = st.multiselect("週報通道", channel_options, default=[c for c in settings.get("weekly_digest_channels", ["inbox"]) if c in channel_options], key="notify_weekly_channels")

    col_save, col_test = st.columns(2)
    if col_save.button("儲存通知設定"):
        save_settings(user_id, {
            "email_enabled": email_enabled,
            "email_to": email_to.strip(),
            "smtp_host": smtp_host.strip(),
            "smtp_port": int(smtp_port),
            "smtp_username": smtp_username.strip(),
            "smtp_use_tls": bool(smtp_use_tls),
            "telegram_enabled": telegram_enabled,
            "telegram_chat_id": telegram_chat_id.strip(),
            "line_enabled": line_enabled,
            "line_user_id": line_user_id.strip(),
            "inbox_enabled": True,
            "price_alert_channels": price_channels or ["inbox"],
            "strategy_alert_channels": strategy_channels or ["inbox"],
            "weekly_digest_channels": weekly_channels or ["inbox"],
        })
        if smtp_password.strip():
            set_secret(user_id, "smtp_password", smtp_password.strip())
        if telegram_token.strip():
            set_secret(user_id, "telegram_bot_token", telegram_token.strip())
        if line_token.strip():
            set_secret(user_id, "line_channel_access_token", line_token.strip())
        st.success("通知設定已儲存")
        st.rerun()

    if col_test.button("傳送測試通知"):
        results = send_notification(
            user_id,
            "Stock Intelligence 測試通知",
            "這是一則測試訊息。若外部通道失敗，Inbox 仍會保留此訊息。",
            severity="info",
            event_type="price_alert",
        )
        st.write([result.__dict__ for result in results])
