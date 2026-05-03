from dotenv import load_dotenv
load_dotenv()  # must run before any import that reads os.getenv at module level

import streamlit as st

from src.auth.auth_manager import delete_session, resolve_session
from src.auth.session_cookie import (
    get_auth_cookie,
    render_clear_auth_cookie,
    render_set_auth_cookie,
)
from src.core.current_user import current_user, current_user_is_admin
from src.ui.theme import apply_theme
from src.ui.sidebar import render_sidebar
from src.ui.pages import alerts_page, dashboard, market_overview_page, settings_page, backtest_page, scanner_page, risk_page, admin_page, workstation_page
from src.ui.pages.login_page import render as render_login

st.set_page_config(
    page_title="Stock Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init theme from saved prefs before CSS injection (avoids one-rerun delay) ──
if "theme" not in st.session_state and "user_id" in st.session_state:
    from src.repositories.preferences_repo import get_preferences as _get_prefs
    _prefs = _get_prefs(st.session_state["user_id"])
    st.session_state["theme"] = _prefs.get("theme", "morandi")

apply_theme()


@st.cache_resource
def _boot_scheduler_if_enabled():
    from src.scheduler import start_background_scheduler

    return start_background_scheduler()


_boot_scheduler_if_enabled()

# ── Persistent auth restore / cookie updates ──
if st.session_state.pop("_clear_auth_cookie", False):
    render_clear_auth_cookie()

pending_cookie = st.session_state.pop("_set_auth_cookie", "")
if pending_cookie:
    render_set_auth_cookie(pending_cookie)

if "user_id" not in st.session_state:
    token = get_auth_cookie()
    restored = resolve_session(token)
    if restored:
        st.session_state["user_id"] = restored["user_id"]
        st.session_state["username"] = restored["username"]
        st.session_state["is_admin"] = restored["is_admin"]
        st.session_state["auth_token"] = token

# ── Auth gate ──
if "user_id" not in st.session_state:
    render_login()
    st.stop()

user_id = current_user()

# ── Sidebar: user info + logout ──
st.sidebar.markdown(f"**Stock Intelligence**")
st.sidebar.caption(f"👤 {st.session_state.get('username', user_id)}")
if st.sidebar.button("登出", use_container_width=True):
    delete_session(st.session_state.get("auth_token") or get_auth_cookie())
    for key in ("user_id", "username", "is_admin", "auth_token"):
        st.session_state.pop(key, None)
    st.session_state["_clear_auth_cookie"] = True
    st.rerun()

st.sidebar.markdown("---")

# ── Navigation ──
pages = ["📊 Dashboard", "🖥️ 綜合看盤", "🌏 大盤總覽", "🔍 掃描器", "🧮 回測", "🛡️ 風控", "🔔 警示", "⚙️ 設定"]
if current_user_is_admin():
    pages.append("👑 管理")

_PAGE_BY_QUERY = {
    "dashboard": "📊 Dashboard",
    "workstation": "🖥️ 綜合看盤",
    "market": "🌏 大盤總覽",
    "scanner": "🔍 掃描器",
    "backtest": "🧮 回測",
    "risk": "🛡️ 風控",
    "alerts": "🔔 警示",
    "settings": "⚙️ 設定",
    "admin": "👑 管理",
}
_QUERY_BY_PAGE = {v: k for k, v in _PAGE_BY_QUERY.items()}

query_page = st.query_params.get("page", "")
if isinstance(query_page, list):
    query_page = query_page[0] if query_page else ""
query_page_key = str(query_page).lower()
query_nav = _PAGE_BY_QUERY.get(query_page_key)
last_applied_query_page = st.session_state.get("_applied_query_page")

pending_nav = st.session_state.pop("_pending_nav_page", None)
pending_ticker = st.session_state.pop("_pending_ticker", None)
pending_applied = False
if pending_nav in pages:
    st.session_state["nav_page"] = pending_nav
    query_page_key = _QUERY_BY_PAGE.get(pending_nav, query_page_key)
    st.query_params["page"] = query_page_key
    st.session_state["_applied_query_page"] = query_page_key
    query_nav = pending_nav
    last_applied_query_page = query_page_key
    pending_applied = True
if pending_ticker:
    st.session_state["sidebar_ticker"] = pending_ticker
    st.session_state["_applied_query_ticker"] = pending_ticker
    st.query_params["ticker"] = pending_ticker

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = query_nav if query_nav in pages else pages[0]
    st.session_state["_applied_query_page"] = query_page_key
elif not pending_applied and query_nav in pages and query_page_key != last_applied_query_page:
    st.session_state["nav_page"] = query_nav
    st.session_state["_applied_query_page"] = query_page_key

page = st.sidebar.radio(
    "頁面",
    pages,
    label_visibility="collapsed",
    key="nav_page",
)
page_query_key = _QUERY_BY_PAGE.get(page)
if page_query_key and query_page_key != page_query_key:
    st.query_params["page"] = page_query_key
    st.session_state["_applied_query_page"] = page_query_key
st.sidebar.markdown("---")

cfg = render_sidebar(user_id)

if page == "📊 Dashboard":
    dashboard.render(cfg, user_id)
elif page == "🖥️ 綜合看盤":
    workstation_page.render(cfg, user_id)
elif page == "🌏 大盤總覽":
    market_overview_page.render()
elif page == "🔍 掃描器":
    scanner_page.render(cfg, user_id)
elif page == "🧮 回測":
    backtest_page.render(cfg, user_id)
elif page == "🛡️ 風控":
    risk_page.render(cfg, user_id)
elif page == "🔔 警示":
    alerts_page.render(user_id)
elif page == "👑 管理":
    admin_page.render(user_id)
else:
    settings_page.render(user_id)
