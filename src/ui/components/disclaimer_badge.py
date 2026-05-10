from __future__ import annotations

import streamlit as st


def render_disclaimer_badge(text: str = "估算值，僅供參考") -> None:
    st.caption(f"⚠ {text}")
