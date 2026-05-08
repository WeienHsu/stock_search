from __future__ import annotations

import streamlit as st


def render_kpi_bar(kpis: list) -> None:
    """Render a compact KPI row using Streamlit metrics."""
    if not kpis:
        return

    cols = st.columns(len(kpis), gap="medium")
    for col, kpi in zip(cols, kpis):
        with col:
            if getattr(kpi, "aria_label", None):
                st.html(f'<span class="sr-only">{kpi.aria_label}</span>')
            st.metric(
                label=kpi.label,
                value=kpi.value,
                delta=kpi.delta,
                delta_color="normal" if kpi.delta_direction in ("up", "down") else "off",
                help=kpi.help,
            )
