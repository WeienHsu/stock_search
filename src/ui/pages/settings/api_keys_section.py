from __future__ import annotations

import streamlit as st

from src.ui.pages.settings.ai_api_section import render_ai_api_section
from src.ui.pages.settings.market_api_section import render_market_api_section


def render_api_keys_section(user_id: str) -> None:
    render_market_api_section(user_id)
    st.divider()
    render_ai_api_section(user_id)
