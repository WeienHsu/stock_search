from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def build_index_sparkline(df: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty:
        color = "#6A9E8A"
        if len(df) >= 2 and float(df["close"].iloc[-1]) < float(df["close"].iloc[0]):
            color = "#C87D6A"
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["close"],
                mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy",
                fillcolor="rgba(106, 158, 138, 0.12)",
                name=title,
            )
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=220,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    return fig


def build_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty and x_col in df.columns and y_col in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode="lines+markers",
                line=dict(color="#5B7FA8", width=2),
                marker=dict(size=5),
                name=title,
            )
        )
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=260,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    return fig


def build_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty and x_col in df.columns and y_col in df.columns:
        colors = ["#6A9E8A" if value >= 0 else "#C87D6A" for value in df[y_col].fillna(0)]
        fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], marker_color=colors, name=title))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        height=280,
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    return fig
