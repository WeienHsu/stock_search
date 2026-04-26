import streamlit as st


def current_user() -> str:
    """Return the authenticated user_id from session state.
    Falls back to 'local' when called outside a Streamlit session (e.g. tests)."""
    try:
        return st.session_state.get("user_id", "local")
    except Exception:
        return "local"


def current_user_is_admin() -> bool:
    try:
        return bool(st.session_state.get("is_admin", False))
    except Exception:
        return False
