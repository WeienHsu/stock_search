from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.morandi_palette import (
    BACKGROUND, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    GREEN, RED, GOLD, MA_COLORS, BLUE, ORANGE, PURPLE, BROWN,
)


def _apply_layout(fig: go.Figure, title: str = "") -> None:
    fig.update_layout(
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(color=TEXT_PRIMARY, size=12),
        title=dict(text=title, font=dict(size=15, color=TEXT_PRIMARY)),
        legend=dict(bgcolor=BACKGROUND, bordercolor=BORDER, borderwidth=1, font=dict(size=11)),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x",
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=BORDER, zeroline=False,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikethickness=1, spikedash="solid", spikecolor="#888",
    )
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False)


# ── Trace builders (return lists of traces; used by both standalone and combined charts) ──

def _main_traces(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
) -> list[go.BaseTraceType]:
    traces: list[go.BaseTraceType] = []
    traces.append(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=GREEN, decreasing_line_color=RED,
        name="K線", showlegend=False,
    ))
    for n in sorted(ma_periods):
        col = f"MA_{n}"
        if col in df.columns:
            traces.append(go.Scatter(
                x=df["date"], y=df[col],
                mode="lines", name=f"MA{n}",
                line=dict(color=MA_COLORS.get(n, TEXT_SECONDARY), width=1.2),
            ))
    if signal_dates:
        sig_df = df[df["date"].isin(signal_dates)].copy()
        if not sig_df.empty:
            traces.append(go.Scatter(
                x=sig_df["date"],
                y=sig_df["low"] * 0.985,
                mode="markers",
                marker=dict(symbol="triangle-up", size=12, color=GOLD),
                name="Strategy D",
            ))
    return traces


def _macd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    colors = [GREEN if v >= 0 else RED for v in df["histogram"].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df["histogram"], marker_color=colors, name="Histogram", showlegend=False),
        go.Scatter(x=df["date"], y=df["macd_line"], mode="lines", line=dict(color=BLUE, width=1.5), name="MACD"),
        go.Scatter(x=df["date"], y=df["signal_line"], mode="lines", line=dict(color=ORANGE, width=1.5), name="Signal"),
    ]


def _kd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    return [
        go.Scatter(x=df["date"], y=df["K"], mode="lines", line=dict(color=PURPLE, width=1.5), name="K"),
        go.Scatter(x=df["date"], y=df["D"], mode="lines", line=dict(color=BROWN, width=1.5), name="D"),
    ]


def _bias_traces(df: pd.DataFrame, period: int) -> list[go.BaseTraceType]:
    col = f"bias_{period}"
    if col not in df.columns:
        return []
    colors = [GREEN if v >= 0 else RED for v in df[col].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df[col], marker_color=colors, name=f"Bias {period}"),
    ]


# ── Combined chart (single figure, synchronized crosshair across all panels) ──

def build_combined_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
    bias_period: int,
    show_macd: bool,
    show_kd: bool,
    show_bias: bool,
) -> go.Figure:
    """Single subplot figure with shared x-axis for synchronized crosshair."""
    panels: list[str] = ["main"]
    if show_macd and "histogram" in df.columns:
        panels.append("macd")
    if show_kd and "K" in df.columns:
        panels.append("kd")
    if show_bias and f"bias_{bias_period}" in df.columns:
        panels.append("bias")

    n_rows = len(panels)
    main_h = 0.50
    other_h = (1.0 - main_h) / max(n_rows - 1, 1) if n_rows > 1 else 1.0
    row_heights = [main_h] + [other_h] * (n_rows - 1)

    panel_titles = {"main": f"{ticker} — K 線圖", "macd": "MACD", "kd": "KD", "bias": f"乖離率 (MA{bias_period})"}
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[panel_titles[p] for p in panels],
    )

    for row_idx, panel in enumerate(panels, start=1):
        if panel == "main":
            for trace in _main_traces(df, ticker, ma_periods, signal_dates):
                fig.add_trace(trace, row=row_idx, col=1)
        elif panel == "macd":
            for trace in _macd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=BORDER, line_width=1, row=row_idx, col=1)
        elif panel == "kd":
            for trace in _kd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=80, line_color=RED, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.add_hline(y=20, line_color=GREEN, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.update_yaxes(range=[0, 100], row=row_idx, col=1)
        elif panel == "bias":
            for trace in _bias_traces(df, bias_period):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=BORDER, line_width=1, row=row_idx, col=1)

    _apply_layout(fig)
    fig.update_layout(height=300 + 200 * (n_rows - 1), showlegend=True)
    fig.update_xaxes(rangeslider_visible=False)
    return fig


# ── Standalone chart wrappers (preserved for backtest_page and other callers) ──

def build_main_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
) -> go.Figure:
    fig = go.Figure()
    for trace in _main_traces(df, ticker, ma_periods, signal_dates):
        fig.add_trace(trace)
    _apply_layout(fig, title=f"{ticker} — K 線圖")
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for trace in _macd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="MACD")
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


def build_kd_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for trace in _kd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="KD")
    fig.add_hline(y=80, line_color=RED,   line_dash="dash", line_width=1, annotation_text="80")
    fig.add_hline(y=20, line_color=GREEN, line_dash="dash", line_width=1, annotation_text="20")
    fig.update_yaxes(range=[0, 100])
    return fig


def build_bias_chart(df: pd.DataFrame, period: int) -> go.Figure:
    col = f"bias_{period}"
    if col not in df.columns:
        return go.Figure()
    fig = go.Figure()
    for trace in _bias_traces(df, period):
        fig.add_trace(trace)
    _apply_layout(fig, title=f"乖離率 (MA{period})")
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig
