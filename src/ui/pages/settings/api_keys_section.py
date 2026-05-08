from __future__ import annotations

import os

import finnhub
import streamlit as st

from src.core.finnhub_mode import current_mode
from src.repositories.user_secrets_repo import clear_secret, get_secret, has_secret, set_secret


def render_api_keys_section(user_id: str) -> None:
    _render_market_sentiment_settings(user_id)
    st.divider()
    _render_ai_settings(user_id)


def _render_market_sentiment_settings(user_id: str) -> None:
    st.markdown("### 市場情緒 API")
    if current_mode() == "global":
        st.info("目前由系統管理者統一設定 Finnhub API key，無需個別配置。")
        return

    key_set = has_secret(user_id, "finnhub_api_key")
    (st.success if key_set else st.warning)(
        "API key 已設定 ✓" if key_set else "尚未設定 Finnhub API key，Dashboard 的市場情緒功能無法使用。"
    )
    new_key = st.text_input("輸入新 API key（儲存後無法查看原始值）", type="password", key="finnhub_key_input", placeholder="留空表示不更換")
    col_save, col_test, col_clear = st.columns(3)
    if col_save.button("儲存金鑰"):
        if new_key.strip():
            set_secret(user_id, "finnhub_api_key", new_key.strip())
            st.success("已儲存")
            st.rerun()
        st.warning("請先輸入 API key")

    if col_test.button("測試連線"):
        test_key = new_key.strip() or get_secret(user_id, "finnhub_api_key")
        if not test_key:
            st.error("尚未設定 API key，無法測試")
        else:
            try:
                finnhub.Client(api_key=test_key).general_news("general", min_id=0)
                st.success("✓ 連線成功")
            except Exception as exc:
                st.error(f"✗ 連線失敗：{exc}")

    if key_set and col_clear.button("移除金鑰"):
        clear_secret(user_id, "finnhub_api_key")
        st.success("已移除")
        st.rerun()


def _render_ai_settings(user_id: str) -> None:
    st.markdown("### AI 解讀設定")
    st.caption("Dashboard 訊號解讀與新聞摘要會依序使用 Anthropic、Gemini、OpenAI；個人金鑰優先於系統 .env 金鑰。")

    providers = [
        ("Anthropic", "anthropic_api_key", "ANTHROPIC_API_KEY", "ai_anthropic_key"),
        ("Gemini", "gemini_api_key", "GEMINI_API_KEY", "ai_gemini_key"),
        ("OpenAI", "openai_api_key", "OPENAI_API_KEY", "ai_openai_key"),
    ]
    pending: dict[str, str] = {}
    clear_names: list[str] = []

    for label, secret_name, env_name, input_key in providers:
        col_status, col_input, col_clear = st.columns([1.4, 2.8, 0.8], vertical_alignment="bottom")
        env_set = bool(os.getenv(env_name, ""))
        user_set = has_secret(user_id, secret_name)
        _render_secret_status(col_status, label, user_set, env_set)
        pending[secret_name] = col_input.text_input(f"{label} API key（留空表示不更換）", type="password", key=input_key).strip()
        if user_set and col_clear.button("移除", key=f"clear_{secret_name}"):
            clear_names.append(secret_name)

    col_save, col_order = st.columns([1, 4])
    col_order.caption(f"目前 provider 順序：{os.getenv('AI_PROVIDER_ORDER', 'anthropic_haiku,gemini_flash,openai,anthropic_sonnet')}")

    if col_save.button("儲存 AI 金鑰"):
        changed = False
        try:
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

    if clear_names:
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
