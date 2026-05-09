from __future__ import annotations

import finnhub
import streamlit as st

from src.core.finnhub_mode import current_mode
from src.repositories.user_secrets_repo import clear_secret, get_secret, has_secret, set_secret


def render_market_api_section(user_id: str) -> None:
    st.markdown("### 市場情緒 API")
    if current_mode() == "global":
        st.info("目前由系統管理者統一設定 Finnhub API key，無需個別配置。")
        return

    key_set = has_secret(user_id, "finnhub_api_key")
    (st.success if key_set else st.warning)(
        "API key 已設定 ✓" if key_set else "尚未設定 Finnhub API key，Dashboard 的市場情緒功能無法使用。"
    )
    new_key = st.text_input(
        "輸入新 API key（儲存後無法查看原始值）",
        type="password",
        key="finnhub_key_input",
        placeholder="留空表示不更換",
    )
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
