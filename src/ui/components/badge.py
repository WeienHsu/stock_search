from __future__ import annotations

from html import escape
from typing import Literal

import streamlit as st

from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens


def render_status_pill(
    text: str,
    kind: Literal["buy", "sell", "neutral", "warning", "info"] = "neutral",
) -> None:
    tokens = get_tokens(get_current_theme())
    colors = {
        "buy": (tokens["semantic_up_soft"], tokens["semantic_up_text"], "▲"),
        "sell": (tokens["semantic_down_soft"], tokens["semantic_down_text"], "▼"),
        "neutral": (tokens["bg_elevated"], tokens["text_secondary"], ""),
        "warning": (tokens["bg_elevated"], tokens["semantic_warning"], "⚠"),
        "info": (tokens["bg_elevated"], tokens["semantic_info"], "ⓘ"),
    }
    bg, fg, icon = colors[kind]
    prefix = f"{icon} " if icon else ""
    aria_prefix = {"buy": "上漲或買進", "sell": "下跌或賣出"}.get(kind, kind)
    safe_text = escape(text)
    st.html(
        (
            f'<span role="status" aria-label="{escape(aria_prefix)} {safe_text}" '
            f'style="display:inline-block; padding:2px 8px; border-radius:12px; '
            f'font-size:11px; font-weight:600; color:{fg}; background:{bg};">'
            f'<span aria-hidden="true">{escape(prefix)}</span>{safe_text}</span>'
        )
    )
