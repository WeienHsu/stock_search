import json

import streamlit as st

from src.auth.auth_manager import SESSION_TTL_SECONDS

COOKIE_NAME = "stock_search_auth"


def get_auth_cookie() -> str:
    try:
        return str(st.context.cookies.get(COOKIE_NAME, ""))
    except Exception:
        return ""


def render_set_auth_cookie(token: str, max_age: int = SESSION_TTL_SECONDS) -> None:
    if not token:
        return
    cookie = (
        f"{COOKIE_NAME}={token}; Max-Age={int(max_age)}; "
        "Path=/; SameSite=Lax"
    )
    _render_cookie_script(cookie)


def render_clear_auth_cookie() -> None:
    cookie = f"{COOKIE_NAME}=; Max-Age=0; Path=/; SameSite=Lax"
    _render_cookie_script(cookie)


def _render_cookie_script(cookie: str) -> None:
    cookie_js = json.dumps(cookie)
    st.html(
        f"""
        <script>
        const cookieValue = {cookie_js};
        document.cookie = cookieValue;
        try {{
          window.parent.document.cookie = cookieValue;
        }} catch (err) {{}}
        </script>
        """,
        unsafe_allow_javascript=True,
    )
