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
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False),
    )


def build_main_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
) -> go.Figure:
    """K-line chart with MA lines and Strategy D signal markers."""
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=GREEN, decreasing_line_color=RED,
        name="K線", showlegend=False,
    ))

    # MA lines
    for n in sorted(ma_periods):
        col = f"MA_{n}"
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[col],
                mode="lines", name=f"MA{n}",
                line=dict(color=MA_COLORS.get(n, TEXT_SECONDARY), width=1.2),
            ))

    # Strategy D signal markers
    if signal_dates:
        sig_df = df[df["date"].isin(signal_dates)].copy()
        if not sig_df.empty:
            fig.add_trace(go.Scatter(
                x=sig_df["date"],
                y=sig_df["low"] * 0.985,
                mode="markers",
                marker=dict(symbol="triangle-up", size=12, color=GOLD),
                name="Strategy D",
            ))

    _apply_layout(fig, title=f"{ticker} — K 線圖")
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    """MACD panel: line + signal + histogram."""
    fig = go.Figure()

    # Histogram bars (colored by sign)
    colors = [GREEN if v >= 0 else RED for v in df["histogram"].fillna(0)]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["histogram"],
        marker_color=colors, name="Histogram", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["macd_line"],
        mode="lines", line=dict(color=BLUE, width=1.5), name="MACD",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["signal_line"],
        mode="lines", line=dict(color=ORANGE, width=1.5), name="Signal",
    ))

    _apply_layout(fig, title="MACD")
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig


def build_kd_chart(df: pd.DataFrame) -> go.Figure:
    """KD panel."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["K"],
        mode="lines", line=dict(color=PURPLE, width=1.5), name="K",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["D"],
        mode="lines", line=dict(color=BROWN, width=1.5), name="D",
    ))

    _apply_layout(fig, title="KD")
    fig.add_hline(y=80, line_color=RED,   line_dash="dash", line_width=1, annotation_text="80")
    fig.add_hline(y=20, line_color=GREEN, line_dash="dash", line_width=1, annotation_text="20")
    fig.update_yaxes(range=[0, 100])
    return fig


def build_bias_chart(df: pd.DataFrame, period: int) -> go.Figure:
    """Bias panel."""
    col = f"bias_{period}"
    if col not in df.columns:
        return go.Figure()

    fig = go.Figure()
    colors = [GREEN if v >= 0 else RED for v in df[col].fillna(0)]
    fig.add_trace(go.Bar(
        x=df["date"], y=df[col],
        marker_color=colors, name=f"Bias {period}",
    ))

    _apply_layout(fig, title=f"乖離率 (MA{period})")
    fig.add_hline(y=0, line_color=BORDER, line_width=1)
    return fig
