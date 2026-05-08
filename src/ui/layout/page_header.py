from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import streamlit as st


@dataclass
class Kpi:
    label: str
    value: str
    delta: str | None = None
    delta_direction: Literal["up", "down", "flat"] | None = None
    help: str | None = None
    aria_label: str | None = None


@dataclass
class Action:
    label: str
    on_click: Callable[[], None] | None = None
    type: Literal["primary", "secondary", "ghost"] = "secondary"
    key: str = ""
    disabled: bool = False
    help: str | None = None


def render_page_header(
    title: str,
    subtitle: str | None = None,
    kpis: list[Kpi] | None = None,
    actions: list[Action] | None = None,
) -> None:
    """Render the shared page header: title, optional actions, optional KPI bar."""
    kpis = kpis or []
    actions = actions or []

    if actions:
        columns = st.columns([5] + [1] * len(actions), vertical_alignment="bottom")
        col_title, col_actions = columns[0], columns[1:]
    else:
        col_title, col_actions = st.container(), []

    with col_title:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)

    for col, action in zip(col_actions, actions):
        with col:
            clicked = st.button(
                action.label,
                key=action.key or f"pageheader_{_slug(action.label)}",
                type="secondary" if action.type == "ghost" else action.type,
                use_container_width=True,
                disabled=action.disabled,
                help=action.help,
            )
            if clicked and action.on_click:
                action.on_click()

    if kpis:
        from src.ui.layout.kpi_bar import render_kpi_bar

        render_kpi_bar(kpis)

    st.divider()


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
