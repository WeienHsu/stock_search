from __future__ import annotations

import streamlit as st

from src.repositories import user_prefs_repo
from src.repositories.notification_settings_repo import get_settings, save_settings

_DIGEST_NS = "digest_settings"
_CHANNEL_OPTIONS = ["inbox", "email", "telegram", "line"]


def render_digest_section(user_id: str) -> None:
    st.markdown("### 每日摘要設定")
    st.caption(
        "啟用後，系統將在盤前（08:30）與 / 或盤後（14:30）自動生成 AI 摘要並推送。"
        "AI 金鑰未設定時自動改為純文字摘要。"
    )

    prefs = user_prefs_repo.get(user_id, _DIGEST_NS)
    notif = get_settings(user_id)

    enabled = st.toggle(
        "啟用每日摘要",
        value=bool(prefs.get("enabled", False)),
        key="digest_enabled",
    )

    col_pre, col_post = st.columns(2)
    with col_pre:
        pre_market = st.checkbox(
            "盤前摘要（08:30）",
            value=bool(prefs.get("pre_market", True)),
            disabled=not enabled,
            key="digest_pre_market",
        )
    with col_post:
        post_market = st.checkbox(
            "盤後摘要（14:30）",
            value=bool(prefs.get("post_market", False)),
            disabled=not enabled,
            key="digest_post_market",
        )

    saved_channels = notif.get("daily_digest_channels", ["inbox"])
    channels = st.multiselect(
        "推送通道",
        _CHANNEL_OPTIONS,
        default=[c for c in saved_channels if c in _CHANNEL_OPTIONS],
        disabled=not enabled,
        key="digest_channels",
        help="通道需先在「通知」tab 完成設定才會生效。",
    )

    st.divider()
    col_save, col_test = st.columns([1, 1])

    if col_save.button("儲存摘要設定", type="primary"):
        user_prefs_repo.set(user_id, _DIGEST_NS, {
            "enabled": enabled,
            "pre_market": pre_market,
            "post_market": post_market,
        })
        notif_updated = {**notif, "daily_digest_channels": channels or ["inbox"]}
        save_settings(user_id, notif_updated)
        st.success("已儲存。")
        st.rerun()

    if col_test.button("立即測試盤前摘要"):
        with st.spinner("生成中…"):
            _test_digest(user_id, "pre_market")


def _test_digest(user_id: str, digest_type: str) -> None:
    try:
        from src.scheduler.jobs.daily_digest import run_daily_digest

        # Temporarily force-enable to bypass disabled guard
        saved = user_prefs_repo.get(user_id, _DIGEST_NS)
        user_prefs_repo.set(user_id, _DIGEST_NS, {**saved, "enabled": True})

        result = run_daily_digest(user_id, digest_type)

        # Restore original prefs
        user_prefs_repo.set(user_id, _DIGEST_NS, saved)

        if result.get("skipped") and result.get("reason") == "already_sent_today":
            st.info("今日已發送過，請明日再試，或清除快取後重新測試。")
        elif result.get("delivered"):
            st.success(f"測試摘要已發送！通道：{result.get('channels')}")
        else:
            st.warning(f"摘要已生成但發送失敗，結果：{result}")
    except Exception as exc:
        st.error(f"測試失敗：{exc}")
