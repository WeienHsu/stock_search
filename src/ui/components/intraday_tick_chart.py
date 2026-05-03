from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data.price_fetcher import fetch_prices_by_interval


def build_intraday_tick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    if not df.empty and {"date", "close"}.issubset(df.columns):
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            line=dict(color="#7A9EB5", width=2),
            name="1m",
        ))
    fig.update_layout(
        title=dict(text=f"{ticker} 即時分時", font=dict(size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        height=240,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#D4CEC8")
    fig.update_yaxes(showgrid=True, gridcolor="#D4CEC8")
    return fig


def render_intraday_tick_chart(ticker: str, *, key: str | None = None) -> None:
    try:
        df = fetch_prices_by_interval(ticker, "1m", period="1M")
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        st.info("1m 分時資料暫不可用")
        return
    chart_key = key or f"intraday_tick_chart_{ticker}"
    st.plotly_chart(build_intraday_tick_chart(df, ticker), use_container_width=True, key=chart_key)
