from __future__ import annotations

import html

import streamlit as st

from src.repositories.source_health_repo import format_health_summary, get_source_health

_STATUS_COLORS = {
    "ok": "#6A9E8A",
    "unavailable": "#C87D6A",
    "unsupported": "#8A8480",
    "unknown": "#8A8480",
}


def render_source_health_badge(source_id: str, label: str | None = None) -> None:
    health = get_source_health(source_id)
    status = str(health.get("last_status") or "unknown")
    color = _STATUS_COLORS.get(status, _STATUS_COLORS["unknown"])
    label_text = label or source_id
    title = format_health_summary(health)
    safe_title = html.escape(title, quote=True)
    safe_label = html.escape(label_text)
    st.markdown(
        f"""
        <span title="{safe_title}" style="
            display:inline-block;
            padding:0.15rem 0.5rem;
            border-radius:999px;
            border:1px solid {color};
            color:{color};
            font-size:0.8rem;
            line-height:1.4;
            margin-right:0.35rem;
            margin-bottom:0.25rem;
        ">{safe_label}</span>
        """,
        unsafe_allow_html=True,
    )
