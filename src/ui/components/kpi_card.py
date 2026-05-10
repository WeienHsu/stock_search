from __future__ import annotations

from typing import Literal

import streamlit as st

from src.ui.components._variants import KpiSize, KpiTone
from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_direction: Literal["up", "down", "flat"] | None = None,
    tone: KpiTone | None = None,
    size: KpiSize = "md",
    suffix_html: str | None = None,
    aria_label: str | None = None,
) -> None:
    """Render a non-standard KPI card for signal dots or score suffixes."""
    tokens = get_tokens(get_current_theme())
    delta_direction = delta_direction or _delta_direction_from_tone(tone)
    sizing = _kpi_size_tokens(size)
    delta_color = {
        "up": tokens["semantic_up_text"],
        "down": tokens["semantic_down_text"],
        "flat": tokens["text_secondary"],
        None: tokens["text_secondary"],
    }[delta_direction]
    arrow = "▲" if delta_direction == "up" else "▼" if delta_direction == "down" else "—"
    delta_html = (
        f'<div style="color:{delta_color}; font-size:{sizing["delta"]}; font-weight:600;">{arrow} {delta}</div>'
        if delta
        else ""
    )
    sr_only = f'<span class="sr-only">{aria_label}</span>' if aria_label else ""
    st.html(
        (
            f"{sr_only}"
            f'<div style="padding:{sizing["padding"]};">'
            f'<div style="color:{tokens["text_tertiary"]}; font-size:{sizing["label"]}; font-weight:600; '
            f'letter-spacing:0.02em; margin-bottom:4px;">{label}</div>'
            f'<div style="color:{tokens["text_primary"]}; font-size:{sizing["value"]}; font-weight:600; '
            f'font-variant-numeric:tabular-nums;">{value}{(" " + suffix_html) if suffix_html else ""}</div>'
            f"{delta_html}"
            "</div>"
        )
    )


def _delta_direction_from_tone(tone: KpiTone | None) -> Literal["up", "down", "flat"] | None:
    if tone == "up":
        return "up"
    if tone == "down":
        return "down"
    if tone == "neutral":
        return "flat"
    return None


def _kpi_size_tokens(size: KpiSize) -> dict[str, str]:
    return {
        "sm": {"padding": "4px 0", "label": "11px", "value": "20px", "delta": "12px"},
        "md": {"padding": "8px 0", "label": "12px", "value": "24px", "delta": "13px"},
        "lg": {"padding": "10px 0", "label": "13px", "value": "30px", "delta": "14px"},
    }[size]
