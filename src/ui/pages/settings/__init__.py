from __future__ import annotations

import streamlit as st

from src.ui.pages.settings.ai_api_section import render_ai_api_section
from src.ui.pages.settings.digest_section import render_digest_section
from src.ui.pages.settings.holdings_section import render_holdings_section
from src.ui.pages.settings.market_api_section import render_market_api_section
from src.ui.pages.settings.notifications_section import render_notifications_section
from src.ui.pages.settings.preferences_section import render_preferences_section
from src.ui.pages.settings.strategy_defaults_section import render_strategy_defaults_section
from src.ui.pages.settings.watchlist_section import render_watchlist_section


def render(user_id: str) -> None:
    st.markdown("## 設定")

    tabs = st.tabs(["自選清單", "持股管理", "每日摘要", "偏好", "策略預設", "API 金鑰", "通知"])
    with tabs[0]:
        render_watchlist_section(user_id)
    with tabs[1]:
        render_holdings_section(user_id)
    with tabs[2]:
        render_digest_section(user_id)
    with tabs[3]:
        render_preferences_section(user_id)
    with tabs[4]:
        render_strategy_defaults_section(user_id)
    with tabs[5]:
        render_market_api_section(user_id)
        st.divider()
        render_ai_api_section(user_id)
    with tabs[6]:
        render_notifications_section(user_id)
