from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.ui.theme.plotly_template import apply_chart_theme, get_chart_palette


def build_index_sparkline(df: pd.DataFrame, title: str) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    if not df.empty:
        color = palette.MORANDI_UP
        fillcolor = palette.FILL_UP
        if len(df) >= 2 and float(df["close"].iloc[-1]) < float(df["close"].iloc[0]):
            color = palette.MORANDI_DOWN
            fillcolor = palette.FILL_DOWN
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["close"],
                mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy",
                fillcolor=fillcolor,
                name=title,
            )
        )
    apply_chart_theme(fig, title=title)
    fig.update_layout(
        height=220,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=palette.BORDER)
    return fig


def build_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    if not df.empty and x_col in df.columns and y_col in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode="lines+markers",
                line=dict(color=palette.BLUE, width=2),
                marker=dict(size=5),
                name=title,
            )
        )
    apply_chart_theme(fig, title=title)
    fig.update_layout(
        height=260,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=True, gridcolor=palette.BORDER)
    return fig


def build_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    if not df.empty and x_col in df.columns and y_col in df.columns:
        colors = [palette.MORANDI_UP if value >= 0 else palette.MORANDI_DOWN for value in df[y_col].fillna(0)]
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], marker_color=colors, name=title))
    apply_chart_theme(fig, title=title)
    fig.update_layout(
        height=280,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=True, gridcolor=palette.BORDER)
    return fig
