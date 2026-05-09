from __future__ import annotations

import os

import streamlit as st

from src.repositories.user_secrets_repo import clear_secret, has_secret, set_secret

AI_PROVIDERS = [
    ("Anthropic", "anthropic_api_key", "ANTHROPIC_API_KEY", "ai_anthropic_key"),
    ("Gemini", "gemini_api_key", "GEMINI_API_KEY", "ai_gemini_key"),
    ("OpenAI", "openai_api_key", "OPENAI_API_KEY", "ai_openai_key"),
]


def render_ai_api_section(user_id: str) -> None:
    st.markdown("### AI 解讀設定")
    st.caption("Dashboard 訊號解讀與新聞摘要會依序使用 Anthropic、Gemini、OpenAI；個人金鑰優先於系統 .env 金鑰。")

    pending: dict[str, str] = {}
    clear_names: list[str] = []
    for label, secret_name, env_name, input_key in AI_PROVIDERS:
        col_status, col_input, col_clear = st.columns([1.4, 2.8, 0.8], vertical_alignment="bottom")
        env_set = bool(os.getenv(env_name, ""))
        user_set = has_secret(user_id, secret_name)
        _render_secret_status(col_status, label, user_set, env_set)
        pending[secret_name] = col_input.text_input(
            f"{label} API key（留空表示不更換）",
            type="password",
            key=input_key,
        ).strip()
        if user_set and col_clear.button("移除", key=f"clear_{secret_name}"):
            clear_names.append(secret_name)

    col_save, col_order = st.columns([1, 4])
    col_order.caption(f"目前 provider 順序：{os.getenv('AI_PROVIDER_ORDER', 'anthropic_haiku,gemini_flash,openai,anthropic_sonnet')}")
    _save_ai_keys(user_id, pending, col_save)
    _clear_ai_keys(user_id, clear_names)


def _save_ai_keys(user_id: str, pending: dict[str, str], col_save) -> None:
    if not col_save.button("儲存 AI 金鑰"):
        return
    try:
        changed = False
        for secret_name, value in pending.items():
            if value:
                set_secret(user_id, secret_name, value)
                changed = True
        if changed:
            st.success("AI 金鑰已儲存")
            st.rerun()
        else:
            st.warning("沒有輸入新的 AI 金鑰")
    except Exception as exc:
        st.error(f"儲存失敗：{exc}")


def _clear_ai_keys(user_id: str, clear_names: list[str]) -> None:
    if not clear_names:
        return
    try:
        for secret_name in clear_names:
            clear_secret(user_id, secret_name)
        st.success("AI 個人金鑰已移除")
        st.rerun()
    except Exception as exc:
        st.error(f"移除失敗：{exc}")


def _render_secret_status(column, label: str, user_set: bool, env_set: bool) -> None:
    if user_set:
        column.success(f"{label} 個人金鑰已設定")
    elif env_set:
        column.info(f"{label} 系統金鑰已設定")
    else:
        column.warning(f"{label} 未設定")
