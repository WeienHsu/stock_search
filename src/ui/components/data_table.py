from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import streamlit as st

from src.ui.components._variants import TableDensity
from src.ui.utils.styler import apply_up_down_style


@dataclass
class ColumnSpec:
    key: str
    label: str
    type: Literal["text", "number", "pct", "progress"] = "text"
    width: Literal["small", "medium", "large"] | int = "medium"
    format: str | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None


def render_data_table(
    df: pd.DataFrame,
    schema: list[ColumnSpec],
    *,
    key: str,
    height: int | None = 520,
    on_select: bool = False,
    styled_df=None,
    density: TableDensity = "default",
    tone_columns: list[str] | None = None,
):
    visible_keys = [column.key for column in schema if column.key in df.columns]
    view = df[visible_keys].copy()
    data = styled_df if styled_df is not None else _style_tone_columns(view, tone_columns or [])
    kwargs = {
        "column_config": {column.key: _column_config(column) for column in schema if column.key in view.columns},
        "hide_index": True,
        "width": "stretch",
        "height": height,
        "key": key,
        "on_select": "rerun" if on_select else "ignore",
        "row_height": _row_height_for_density(density),
    }
    if on_select:
        kwargs["selection_mode"] = "single-row"
    return st.dataframe(data, **kwargs)


def _row_height_for_density(density: TableDensity) -> int | None:
    return {"compact": 28, "default": None}[density]


def _style_tone_columns(df: pd.DataFrame, columns: list[str]):
    return apply_up_down_style(df, columns)


def _column_config(column: ColumnSpec):
    if column.type == "number":
        return st.column_config.NumberColumn(column.label, format=column.format or "%.2f", width=column.width)
    if column.type == "pct":
        return st.column_config.NumberColumn(column.label, format=column.format or "%+.2f%%", width=column.width)
    if column.type == "progress":
        return st.column_config.ProgressColumn(
            column.label,
            format=column.format or "%d",
            min_value=column.min_value if column.min_value is not None else 0,
            max_value=column.max_value if column.max_value is not None else 100,
            width=column.width,
        )
    return st.column_config.TextColumn(column.label, width=column.width)
