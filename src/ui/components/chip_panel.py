from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data.chip_fetcher import fetch_chip_snapshot, is_taiwan_ticker


def render_chip_panel(ticker: str) -> None:
    if not is_taiwan_ticker(ticker):
        return

    st.markdown("---")
    with st.expander("籌碼面（外資 / 投信 / 融資）", expanded=True):
        with st.spinner("載入籌碼資料…"):
            try:
                data = fetch_chip_snapshot(ticker)
            except Exception as exc:
                st.info(f"籌碼資料暫不可用：{exc}")
                return

        if not data.get("supported"):
            return

        institutional = data.get("institutional")
        margin = data.get("margin")
        summary = data.get("summary", {})
        if not isinstance(institutional, pd.DataFrame):
            institutional = pd.DataFrame()
        if not isinstance(margin, pd.DataFrame):
            margin = pd.DataFrame()

        _render_summary(summary)

        col_flow, col_margin = st.columns([1.4, 1])
        with col_flow:
            if institutional.empty:
                st.info("近 5 日法人買賣超資料暫不可用")
            else:
                st.plotly_chart(_institutional_flow_chart(institutional), use_container_width=True)
        with col_margin:
            if margin.empty:
                st.info("近 20 日融資融券資料暫不可用")
            else:
                st.plotly_chart(_margin_trend_chart(margin), use_container_width=True)


def _render_summary(summary: dict) -> None:
    cols = st.columns(3)
    cols[0].metric("外資 5日累計", _lots_text(summary.get("foreign_5d_lots", 0)))
    cols[1].metric("投信 5日累計", _lots_text(summary.get("investment_trust_5d_lots", 0)))
    cols[2].metric(
        "融資增減",
        _lots_text(summary.get("margin_change_lots", 0)),
        f"{summary.get('margin_change_pct', 0):+.2f}%",
    )
    st.caption(f"融資趨勢：{summary.get('margin_trend', '持平')}；資料通常於收盤後更新，盤中可能仍是前一交易日。")


def _institutional_flow_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    foreign = pd.to_numeric(df["foreign_net_lots"], errors="coerce").fillna(0)
    investment = pd.to_numeric(df["investment_trust_net_lots"], errors="coerce").fillna(0)
    fig.add_trace(go.Bar(
        x=df["date"],
        y=foreign,
        name="外資",
        marker_color=["#7DAA92" if value >= 0 else "#C47E7E" for value in foreign],
    ))
    fig.add_trace(go.Bar(
        x=df["date"],
        y=investment,
        name="投信",
        marker_color=["#6A9E8A" if value >= 0 else "#C87D6A" for value in investment],
    ))
    _apply_chip_layout(fig, "近 5 日法人買賣超（張）")
    fig.update_layout(barmode="group", height=260)
    fig.add_hline(y=0, line_color="#D4CEC8", line_width=1)
    return fig


def _margin_trend_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    margin_balance = pd.to_numeric(df["margin_balance"], errors="coerce")
    short_balance = pd.to_numeric(df.get("short_balance", pd.Series(dtype=float)), errors="coerce")
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=margin_balance,
        mode="lines+markers",
        name="融資餘額",
        line=dict(color="#7A9EB5", width=2),
    ))
    if short_balance.notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=short_balance,
            mode="lines+markers",
            name="融券餘額",
            line=dict(color="#A89070", width=1.5),
            yaxis="y2",
        ))
        fig.update_layout(
            yaxis2=dict(
                title="融券",
                overlaying="y",
                side="right",
                showgrid=False,
            )
        )
    title = "近 20 日融資融券餘額（張）" if len(df) >= 2 else "最新融資融券餘額（張）"
    _apply_chip_layout(fig, title)
    fig.update_layout(height=260)
    return fig


def _apply_chip_layout(fig: go.Figure, title: str) -> None:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#D4CEC8")
    fig.update_yaxes(showgrid=True, gridcolor="#D4CEC8")


def _lots_text(value: float) -> str:
    value = float(value or 0)
    if abs(value) >= 10_000:
        return f"{value / 10_000:+.2f}萬張"
    return f"{value:+,.0f}張"
