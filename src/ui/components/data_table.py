from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import streamlit as st


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
):
    view = df[[column.key for column in schema if column.key in df.columns]].copy()
    kwargs = {
        "column_config": {column.key: _column_config(column) for column in schema if column.key in view.columns},
        "hide_index": True,
        "use_container_width": True,
        "height": height,
        "key": key,
        "on_select": "rerun" if on_select else "ignore",
    }
    if on_select:
        kwargs["selection_mode"] = "single-row"
    return st.dataframe(view, **kwargs)


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
