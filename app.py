import streamlit as st

from src.core.current_user import current_user, current_user_is_admin
from src.ui.theme import apply_theme
from src.ui.sidebar import render_sidebar
from src.ui.pages import dashboard, settings_page, backtest_page, scanner_page, risk_page, admin_page
from src.ui.pages.login_page import render as render_login

st.set_page_config(
    page_title="Stock Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ── Auth gate ──
if "user_id" not in st.session_state:
    render_login()
    st.stop()

user_id = current_user()

# ── Sidebar: user info + logout ──
st.sidebar.markdown(f"**Stock Intelligence**")
st.sidebar.caption(f"👤 {st.session_state.get('username', user_id)}")
if st.sidebar.button("登出", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# ── Navigation ──
pages = ["📊 Dashboard", "🔍 掃描器", "🧮 回測", "🛡️ 風控", "⚙️ 設定"]
if current_user_is_admin():
    pages.append("👑 管理")

page = st.sidebar.radio(
    "",
    pages,
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
elif page == "👑 管理":
    admin_page.render(user_id)
else:
    settings_page.render(user_id)
