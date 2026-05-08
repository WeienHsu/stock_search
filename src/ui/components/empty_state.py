from __future__ import annotations

import html

import streamlit as st


def render_empty_state(
    icon: str,
    title: str,
    description: str,
    action_label: str | None = None,
    action_key: str | None = None,
    action_type: str = "primary",
) -> bool:
    """Render a reusable empty state and return True when its action is clicked."""
    safe_icon = html.escape(icon)
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    with st.container(border=True):
        st.html(
            (
                '<div role="status" aria-live="polite" style="text-align:center; padding:32px 16px;">'
                f'<div aria-hidden="true" style="font-size:32px; margin-bottom:8px; opacity:0.6;">{safe_icon}</div>'
                f'<div style="font-size:16px; font-weight:600; margin-bottom:4px;">{safe_title}</div>'
                f'<div style="font-size:14px; color:var(--text-secondary); margin-bottom:16px;">{safe_description}</div>'
                "</div>"
            )
        )
        if action_label:
            return st.button(
                action_label,
                key=action_key or f"empty_{_slug(action_label)}",
                type=action_type,
                use_container_width=True,
            )
    return False


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
