from __future__ import annotations

import html
from typing import Literal

import streamlit as st

EmptyStateIcon = Literal["search", "data", "chart", "alert", "user", "settings"]

_ICON_SVGS: dict[str, str] = {
    "search": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m20 20-3.5-3.5"></path></svg>',
    "data": '<svg viewBox="0 0 24 24" aria-hidden="true"><ellipse cx="12" cy="5" rx="8" ry="3"></ellipse><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"></path><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"></path></svg>',
    "chart": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V5"></path><path d="M4 19h16"></path><path d="m7 15 3-4 3 2 4-7"></path></svg>',
    "alert": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.3 4.3 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>',
    "user": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4"></circle><path d="M4 21c1.5-4 4.1-6 8-6s6.5 2 8 6"></path></svg>',
    "settings": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2 2-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V20h-4v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1-2-2 .1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H4v-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1 2-2 .1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V4h4v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1 2 2-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1v4h-.1a1.7 1.7 0 0 0-1.5 1Z"></path></svg>',
}


def render_empty_state(
    icon: EmptyStateIcon | str,
    title: str,
    description: str,
    action_label: str | None = None,
    action_key: str | None = None,
    action_type: str = "primary",
) -> bool:
    """Render a reusable empty state and return True when its action is clicked."""
    icon_html = _icon_html(icon)
    safe_title = html.escape(title)
    safe_description = html.escape(description)
    with st.container(border=True):
        st.html(
            (
                '<div role="status" aria-live="polite" style="text-align:center; padding:32px 16px;">'
                f"{icon_html}"
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
                width="stretch",
            )
    return False


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def _icon_html(icon: str) -> str:
    if icon in _ICON_SVGS:
        return (
            '<div class="empty-state-icon">'
            f"{_ICON_SVGS[icon]}"
            "</div>"
        )
    return (
        '<div aria-hidden="true" style="font-size:32px; margin-bottom:8px; opacity:0.6;">'
        f"{html.escape(icon)}</div>"
    )
