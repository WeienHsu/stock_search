from __future__ import annotations

import streamlit as st

from src.ui.pages.settings.api_keys_section import render_api_keys_section
from src.ui.pages.settings.notifications_section import render_notifications_section
from src.ui.pages.settings.preferences_section import render_preferences_section
from src.ui.pages.settings.strategy_defaults_section import render_strategy_defaults_section
from src.ui.pages.settings.watchlist_section import render_watchlist_section


def render(user_id: str) -> None:
    st.markdown("## 設定")

    tabs = st.tabs(["自選清單", "偏好", "策略預設", "API 金鑰", "通知"])
    with tabs[0]:
        render_watchlist_section(user_id)
    with tabs[1]:
        render_preferences_section(user_id)
    with tabs[2]:
        render_strategy_defaults_section(user_id)
    with tabs[3]:
        render_api_keys_section(user_id)
    with tabs[4]:
        render_notifications_section(user_id)
