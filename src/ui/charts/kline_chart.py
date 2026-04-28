from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _build_rangebreaks(df: pd.DataFrame) -> list[dict]:
    """Return Plotly rangebreaks that skip weekends and market holidays."""
    if df.empty or "date" not in df.columns:
        return []
    try:
        dates = pd.to_datetime(df["date"].astype(str).str[:10])
        min_d, max_d = dates.min(), dates.max()
        all_weekdays = pd.date_range(min_d, max_d, freq="B")  # business days Mon-Fri
        trading_set = set(dates.dt.strftime("%Y-%m-%d"))
        holidays = [d.strftime("%Y-%m-%d") for d in all_weekdays if d.strftime("%Y-%m-%d") not in trading_set]
        breaks: list[dict] = [dict(bounds=["sat", "mon"])]
        if holidays:
            breaks.append(dict(values=holidays))
        return breaks
    except Exception:
        return []


def _get_palette():
    try:
        import streamlit as st
        if st.session_state.get("theme") == "dark":
            import config.dark_palette as P
            return P
    except Exception:
        pass
    import config.morandi_palette as P
    return P


def _apply_layout(fig: go.Figure, title: str = "") -> None:
    P = _get_palette()
    fig.update_layout(
        paper_bgcolor=P.BACKGROUND,
        plot_bgcolor=P.BACKGROUND,
        font=dict(color=P.TEXT_PRIMARY, size=12),
        title=dict(text=title, font=dict(size=15, color=P.TEXT_PRIMARY)),
        legend=dict(bgcolor=P.BACKGROUND, bordercolor=P.BORDER, borderwidth=1, font=dict(size=11)),
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="x",
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=P.BORDER, zeroline=False,
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikethickness=1, spikedash="solid", spikecolor="#888",
    )
    fig.update_yaxes(showgrid=True, gridcolor=P.BORDER, zeroline=False)


# ── Trace builders ──

def _main_traces(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
) -> list[go.BaseTraceType]:
    P = _get_palette()
    traces: list[go.BaseTraceType] = []
    traces.append(go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=P.GREEN, decreasing_line_color=P.RED,
        name="K線", showlegend=False,
    ))
    for n in sorted(ma_periods):
        col = f"MA_{n}"
        if col in df.columns:
            traces.append(go.Scatter(
                x=df["date"], y=df[col],
                mode="lines", name=f"MA{n}",
                line=dict(color=P.MA_COLORS.get(n, P.TEXT_SECONDARY), width=1.2),
            ))
    return traces


def _signal_traces_below(
    df: pd.DataFrame,
    signal_dates: list[str],
) -> list[go.BaseTraceType]:
    """Signal markers below K-line — used only by standalone build_main_chart."""
    P = _get_palette()
    sig_df = df[df["date"].isin(signal_dates)].copy()
    if sig_df.empty:
        return []
    return [go.Scatter(
        x=sig_df["date"],
        y=sig_df["low"] * 0.985,
        mode="markers",
        marker=dict(symbol="triangle-up", size=15, color=P.GOLD, line=dict(color="#ffffff", width=1)),
        name="Strategy D",
    )]


def _macd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    P = _get_palette()
    colors = [P.GREEN if v >= 0 else P.RED for v in df["histogram"].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df["histogram"], marker_color=colors, name="Histogram", showlegend=False),
        go.Scatter(x=df["date"], y=df["macd_line"], mode="lines", line=dict(color=P.BLUE, width=1.5), name="MACD"),
        go.Scatter(x=df["date"], y=df["signal_line"], mode="lines", line=dict(color=P.ORANGE, width=1.5), name="Signal"),
    ]


def _kd_traces(df: pd.DataFrame) -> list[go.BaseTraceType]:
    P = _get_palette()
    return [
        go.Scatter(x=df["date"], y=df["K"], mode="lines", line=dict(color=P.PURPLE, width=1.5), name="K"),
        go.Scatter(x=df["date"], y=df["D"], mode="lines", line=dict(color=P.BROWN, width=1.5), name="D"),
    ]


def _bias_traces(df: pd.DataFrame, period: int) -> list[go.BaseTraceType]:
    P = _get_palette()
    col = f"bias_{period}"
    if col not in df.columns:
        return []
    colors = [P.GREEN if v >= 0 else P.RED for v in df[col].fillna(0)]
    return [
        go.Bar(x=df["date"], y=df[col], marker_color=colors, name=f"Bias {period}"),
    ]


# ── Combined chart ──

def build_combined_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
    bias_period: int,
    show_macd: bool,
    show_kd: bool,
    show_bias: bool,
    x_range_start: str | None = None,
    period: str = "",
    sell_dates: list[str] | None = None,
    show_rangeslider: bool = True,
) -> go.Figure:
    """Combined subplot figure with shared x-axis.

    When show_rangeslider=False the data is assumed to be pre-sliced to the
    selected period, so the Y-axis auto-fits naturally (no rangeslider needed).
    When show_rangeslider=True the full 5Y dataset is expected and the bottom
    rangeslider lets the user navigate the full history.
    """
    P = _get_palette()
    sell_dates = sell_dates or []

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

    panel_titles = {
        "main": f"{ticker} — K 線圖",
        "macd": "MACD",
        "kd": "KD",
        "bias": f"乖離率 (MA{bias_period})",
    }
    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=[panel_titles[p] for p in panels],
    )

    for row_idx, panel in enumerate(panels, start=1):
        if panel == "main":
            for trace in _main_traces(df, ticker, ma_periods):
                fig.add_trace(trace, row=row_idx, col=1)
        elif panel == "macd":
            for trace in _macd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=P.BORDER, line_width=1, row=row_idx, col=1)
        elif panel == "kd":
            for trace in _kd_traces(df):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=80, line_color=P.RED, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.add_hline(y=20, line_color=P.GREEN, line_dash="dash", line_width=1, row=row_idx, col=1)
            fig.update_yaxes(range=[0, 100], row=row_idx, col=1)
        elif panel == "bias":
            for trace in _bias_traces(df, bias_period):
                fig.add_trace(trace, row=row_idx, col=1)
            fig.add_hline(y=0, line_color=P.BORDER, line_width=1, row=row_idx, col=1)

    date_set = set(df["date"].astype(str)) if not df.empty else set()

    # ── Buy signal: ▼ at top, coral-orange vertical lines ──
    if signal_dates:
        for sig_date in signal_dates:
            if str(sig_date)[:10] not in date_set:
                continue
            fig.add_annotation(
                x=sig_date, y=1.0,
                xref="x", yref="y domain",
                yanchor="top", text="▼", showarrow=False,
                font=dict(color=P.GOLD, size=16, family="sans-serif"),
            )
            fig.add_vline(
                x=sig_date, line_dash="dot",
                line_color=P.GOLD, line_width=1.5, opacity=0.6,
            )

    # ── Sell signal: ▲ at bottom, steel-blue vertical lines ──
    sell_color = getattr(P, "SIGNAL_SELL", "#5B7FA8")
    if sell_dates:
        for sell_date in sell_dates:
            if str(sell_date)[:10] not in date_set:
                continue
            fig.add_annotation(
                x=sell_date, y=0.0,
                xref="x", yref="y domain",
                yanchor="bottom", text="▲", showarrow=False,
                font=dict(color=sell_color, size=16, family="sans-serif"),
            )
            fig.add_vline(
                x=sell_date, line_dash="dot",
                line_color=sell_color, line_width=1.5, opacity=0.6,
            )

    _apply_layout(fig)
    fig.update_layout(
        height=300 + 200 * (n_rows - 1),
        showlegend=True,
        uirevision=f"{ticker}_{period}",
    )

    rangebreaks = _build_rangebreaks(df)
    if show_rangeslider and not df.empty:
        # Full-history mode: show rangeslider, set initial view via x_range_start
        end_date = df["date"].iloc[-1]
        fig.update_xaxes(
            rangeslider=dict(
                visible=True,
                thickness=0.04,
                bgcolor=P.SURFACE,
                bordercolor=P.BORDER,
                borderwidth=1,
            ),
            rangebreaks=rangebreaks,
        )
        if x_range_start:
            fig.update_xaxes(range=[x_range_start, end_date], autorange=False)
    else:
        # Auto-Y mode: data is pre-sliced, let Plotly auto-range both axes
        fig.update_xaxes(rangeslider_visible=False, rangebreaks=rangebreaks)

    return fig


# ── Standalone chart wrappers (for backtest_page and other callers) ──

def build_main_chart(
    df: pd.DataFrame,
    ticker: str,
    ma_periods: list[int],
    signal_dates: list[str],
) -> go.Figure:
    fig = go.Figure()
    for trace in _main_traces(df, ticker, ma_periods):
        fig.add_trace(trace)
    if signal_dates:
        for trace in _signal_traces_below(df, signal_dates):
            fig.add_trace(trace)
    _apply_layout(fig, title=f"{ticker} — K 線圖")
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=_build_rangebreaks(df))
    return fig


def build_macd_chart(df: pd.DataFrame) -> go.Figure:
    P = _get_palette()
    fig = go.Figure()
    for trace in _macd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="MACD")
    fig.add_hline(y=0, line_color=P.BORDER, line_width=1)
    return fig


def build_kd_chart(df: pd.DataFrame) -> go.Figure:
    P = _get_palette()
    fig = go.Figure()
    for trace in _kd_traces(df):
        fig.add_trace(trace)
    _apply_layout(fig, title="KD")
    fig.add_hline(y=80, line_color=P.RED,   line_dash="dash", line_width=1, annotation_text="80")
    fig.add_hline(y=20, line_color=P.GREEN, line_dash="dash", line_width=1, annotation_text="20")
    fig.update_yaxes(range=[0, 100])
    return fig


def build_bias_chart(df: pd.DataFrame, period: int) -> go.Figure:
    P = _get_palette()
    col = f"bias_{period}"
    if col not in df.columns:
        return go.Figure()
    fig = go.Figure()
    for trace in _bias_traces(df, period):
        fig.add_trace(trace)
    _apply_layout(fig, title=f"乖離率 (MA{period})")
    fig.add_hline(y=0, line_color=P.BORDER, line_width=1)
    return fig
