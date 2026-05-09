from __future__ import annotations

import streamlit as st


def render_skeleton(lines: int = 3, *, height: int = 16, key_prefix: str = "skeleton") -> None:
    for idx in range(max(1, lines)):
        width = "72%" if idx == lines - 1 and lines > 1 else "100%"
        st.html(
            f'<span class="skeleton-block" data-testid="{key_prefix}_{idx}" '
            f'style="--skeleton-height:{height}px; width:{width}; margin:8px 0;"></span>'
        )
