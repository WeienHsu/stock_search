from __future__ import annotations

from html import escape

import streamlit as st

from src.ui.components._variants import LEGACY_STATUS_KIND_TO_VARIANT, LegacyStatusKind, StatusPillSize, StatusVariant
from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens


def render_status_pill(
    text: str,
    kind: LegacyStatusKind | None = None,
    *,
    variant: StatusVariant | None = None,
    size: StatusPillSize = "sm",
) -> None:
    tokens = get_tokens(get_current_theme())
    resolved_variant = _resolve_status_variant(kind, variant)
    colors = {
        "success": (tokens["semantic_up_soft"], tokens["semantic_up_text"], "▲"),
        "danger": (tokens["semantic_down_soft"], tokens["semantic_down_text"], "▼"),
        "neutral": (tokens["bg_elevated"], tokens["text_secondary"], ""),
        "warning": (tokens["bg_elevated"], tokens["semantic_warning"], "⚠"),
        "info": (tokens["bg_elevated"], tokens["semantic_info"], "ⓘ"),
    }
    bg, fg, icon = colors[resolved_variant]
    font_size, padding = _status_pill_size(size)
    prefix = f"{icon} " if icon else ""
    aria_prefix = _status_pill_aria_label(kind, resolved_variant)
    safe_text = escape(text)
    st.html(
        (
            f'<span role="status" aria-label="{escape(aria_prefix)} {safe_text}" '
            f'style="display:inline-block; padding:{padding}; border-radius:12px; '
            f'font-size:{font_size}; font-weight:600; color:{fg}; background:{bg};">'
            f'<span aria-hidden="true">{escape(prefix)}</span>{safe_text}</span>'
        )
    )


def _resolve_status_variant(kind: LegacyStatusKind | str | None, variant: StatusVariant | None) -> StatusVariant:
    if variant:
        return variant
    return LEGACY_STATUS_KIND_TO_VARIANT.get(str(kind or "neutral"), "neutral")


def _status_pill_size(size: StatusPillSize) -> tuple[str, str]:
    return {
        "sm": ("11px", "2px 8px"),
        "md": ("12px", "4px 10px"),
    }[size]


def _status_pill_aria_label(kind: LegacyStatusKind | str | None, variant: StatusVariant) -> str:
    if kind == "buy":
        return "上漲或買進"
    if kind == "sell":
        return "下跌或賣出"
    return {
        "success": "success",
        "danger": "danger",
        "neutral": "neutral",
        "warning": "warning",
        "info": "info",
    }[variant]
