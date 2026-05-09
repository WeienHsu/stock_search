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
from src.ui.nav.keyboard_shortcuts import inject_shortcuts
from src.ui.nav.page_keys import (
    ADMIN,
    ALERTS,
    BACKTEST,
    DASHBOARD,
    KEY_BY_LABEL,
    LABEL_BY_KEY,
    MARKET,
    RISK,
    SCANNER,
    SETTINGS,
    TODAY,
    WORKSTATION,
)
from src.ui.pages import alerts_page, stock_page, market_overview_page, settings, backtest_page, scanner_page, risk_page, admin_page, workstation_page, today_page
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

st.sidebar.divider()

# ── Navigation ──
def _query_value(name: str) -> str:
    value = st.query_params.get(name, "")
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


page_by_key = {
    TODAY: st.Page(lambda: today_page.render(cfg, user_id), title="Today", icon="🌅", url_path=TODAY, default=True),
    DASHBOARD: st.Page(lambda: stock_page.render(cfg, user_id), title="Dashboard", icon="📊", url_path=DASHBOARD),
    WORKSTATION: st.Page(lambda: workstation_page.render(cfg, user_id), title="綜合看盤", icon="🖥️", url_path=WORKSTATION),
    MARKET: st.Page(market_overview_page.render, title="大盤總覽", icon="🌏", url_path=MARKET),
    SCANNER: st.Page(lambda: scanner_page.render(cfg, user_id), title="掃描器", icon="🔍", url_path=SCANNER),
    BACKTEST: st.Page(lambda: backtest_page.render(cfg, user_id), title="回測", icon="🧮", url_path=BACKTEST),
    RISK: st.Page(lambda: risk_page.render(cfg, user_id), title="風控", icon="🛡️", url_path=RISK),
    ALERTS: st.Page(lambda: alerts_page.render(user_id), title="警示", icon="🔔", url_path=ALERTS),
    SETTINGS: st.Page(lambda: settings.render(user_id), title="設定", icon="⚙️", url_path=SETTINGS),
}
if current_user_is_admin():
    page_by_key[ADMIN] = st.Page(lambda: admin_page.render(user_id), title="管理", icon="👑", url_path=ADMIN)

navigation_sections = {
    "Workspace": [page_by_key[TODAY], page_by_key[DASHBOARD], page_by_key[WORKSTATION], page_by_key[MARKET]],
    "Analysis": [page_by_key[SCANNER], page_by_key[BACKTEST], page_by_key[RISK]],
    "Settings": [page_by_key[ALERTS], page_by_key[SETTINGS]] + ([page_by_key[ADMIN]] if ADMIN in page_by_key else []),
}
selected_page = st.navigation(navigation_sections, position="sidebar", expanded=True)
inject_shortcuts()
st.sidebar.divider()

pending_nav = st.session_state.pop("_pending_nav_page", None)
pending_ticker = st.session_state.pop("_pending_ticker", None)
if pending_ticker:
    st.session_state["sidebar_ticker"] = pending_ticker
    st.session_state["_applied_query_ticker"] = pending_ticker
target_key = KEY_BY_LABEL.get(str(pending_nav), "")

legacy_page_key = _query_value("page").lower()
legacy_aliases = {"stock": DASHBOARD, **{key: key for key in LABEL_BY_KEY}}
legacy_target = legacy_aliases.get(legacy_page_key, "")
if not target_key and legacy_target:
    target_key = legacy_target

if target_key and target_key in page_by_key:
    query_params = {}
    ticker = pending_ticker or _query_value("ticker")
    if ticker:
        query_params["ticker"] = ticker
    st.switch_page(page_by_key[target_key], query_params=query_params or None)

cfg = render_sidebar(user_id)
selected_page.run()
