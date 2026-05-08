from typing import Literal

import streamlit as st

from src.ui.theme.styles import inject_css
from src.ui.theme.tokens import get_tokens

ThemeName = Literal["morandi", "dark"]

_VALID_THEMES = {"morandi", "dark", "system"}


def get_current_theme() -> ThemeName:
    """Return the effective app theme."""
    theme = st.session_state.get("theme", "morandi")
    if theme == "system":
        return _system_theme()
    return theme if theme in {"morandi", "dark"} else "morandi"


def apply_theme() -> None:
    """Inject app-wide CSS once per rerun."""
    raw_theme = st.session_state.get("theme", "morandi")
    if raw_theme not in _VALID_THEMES:
        raw_theme = "morandi"
        st.session_state["theme"] = raw_theme

    effective_theme = get_current_theme()
    st.session_state["_resolved_system_theme"] = effective_theme
    inject_css(effective_theme)


def _system_theme() -> ThemeName:
    try:
        theme_type = str(st.context.theme.get("type") or "").lower()
    except Exception:
        theme_type = ""
    return "dark" if theme_type == "dark" else "morandi"
