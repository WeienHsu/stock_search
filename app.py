import streamlit as st

from src.core.current_user import current_user
from src.ui.theme import apply_theme
from src.ui.sidebar import render_sidebar
from src.ui.pages import dashboard, settings_page, backtest_page, scanner_page, risk_page

st.set_page_config(
    page_title="Stock Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

user_id = current_user()

# ── Navigation ──
page = st.sidebar.radio(
    "",
    ["📊 Dashboard", "🔍 掃描器", "🧮 回測", "🛡️ 風控", "⚙️ 設定"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")

cfg = render_sidebar(user_id)

if page == "📊 Dashboard":
    dashboard.render(cfg, user_id)
elif page == "🔍 掃描器":
    scanner_page.render(cfg, user_id)
elif page == "🧮 回測":
    backtest_page.render(cfg, user_id)
elif page == "🛡️ 風控":
    risk_page.render(cfg, user_id)
else:
    settings_page.render(user_id)
