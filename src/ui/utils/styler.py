from __future__ import annotations

import pandas as pd

from src.ui.theme import get_current_theme
from src.ui.theme.tokens import get_tokens
from src.ui.utils.format_a11y import format_percent


def apply_up_down_style(df: pd.DataFrame, columns: list[str], theme: str | None = None):
    tokens = get_tokens(theme or get_current_theme())
    targets = [column for column in columns if column in df.columns]
    if not targets:
        return df

    def _color(value):
        if pd.isna(value) or value == 0:
            return f"color: {tokens['text_secondary']}"
        if value > 0:
            return f"color: {tokens['semantic_up_text']}; font-weight: 600"
        return f"color: {tokens['semantic_down_text']}; font-weight: 600"

    return df.style.map(_color, subset=targets)


def style_pct_change(df: pd.DataFrame, columns: list[str], theme: str | None = None):
    targets = [column for column in columns if column in df.columns]
    styled = apply_up_down_style(df, targets, theme=theme)
    if not targets:
        return styled
    return (
        styled
        .format({column: format_percent for column in targets})
    )
