from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Literal

import streamlit as st


@contextmanager
def section(
    title: str | None = None,
    *,
    level: Literal["primary", "secondary", "ghost"] = "secondary",
    footer: str | None = None,
    border: bool = True,
) -> Iterator:
    """Render a semantic section container."""
    use_border = border and level == "secondary"
    container = st.container(border=use_border)
    with container:
        if title:
            prefix = "###" if level == "primary" else "####"
            st.markdown(f"{prefix} {title}")
        yield container
        if footer:
            st.caption(footer)
