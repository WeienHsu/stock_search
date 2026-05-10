from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.data.chip_fetcher import fetch_chip_snapshot, is_taiwan_ticker
from src.repositories.chip_snapshot_repo import list_recent_snapshots
from src.ui.theme.plotly_template import apply_chart_theme, get_chart_palette


def render_chip_panel(ticker: str, *, use_expander: bool = True, chart_layout: str = "columns") -> None:
    if not is_taiwan_ticker(ticker):
        return

    def _render_content() -> None:
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
        source_statuses = data.get("source_statuses", {})
        if not isinstance(institutional, pd.DataFrame):
            institutional = pd.DataFrame()
        if not isinstance(margin, pd.DataFrame):
            margin = pd.DataFrame()

        _render_summary(summary, institutional, margin)
        _render_source_statuses(source_statuses)

        history = _snapshot_history(ticker)
        if len(history) >= 2:
            if chart_layout == "stacked":
                st.plotly_chart(_historical_institutional_chart(history), width="stretch")
                st.plotly_chart(_historical_margin_chart(history), width="stretch")
            else:
                col_flow, col_margin = st.columns([1.4, 1])
                with col_flow:
                    st.plotly_chart(_historical_institutional_chart(history), width="stretch")
                with col_margin:
                    st.plotly_chart(_historical_margin_chart(history), width="stretch")
        else:
            _render_current_snapshot(institutional, margin, data, chart_layout=chart_layout)

    if use_expander:
        st.divider()
        with st.expander("籌碼面（外資 / 投信 / 融資）", expanded=True):
            _render_content()
    else:
        _render_content()


def _render_summary(summary: dict, institutional: pd.DataFrame, margin: pd.DataFrame) -> None:
    cols = st.columns(3)
    cols[0].metric("外資 5日累計", _lots_text(summary.get("foreign_5d_lots") if not institutional.empty else None))
    cols[1].metric("投信 5日累計", _lots_text(summary.get("investment_trust_5d_lots") if not institutional.empty else None))
    margin_change = summary.get("margin_change_lots") if not margin.empty else None
    margin_change_pct = summary.get("margin_change_pct") if not margin.empty else None
    cols[2].metric(
        "融資增減",
        _lots_text(margin_change),
        _pct_delta_text(margin_change_pct),
    )
    st.caption(f"融資趨勢：{summary.get('margin_trend', '持平')}；資料通常於收盤後更新，盤中可能仍是前一交易日。")


def _render_source_statuses(statuses: dict) -> None:
    if not statuses:
        return
    for label, key in [("法人", "institutional"), ("融資", "margin"), ("外資持股", "major_holder")]:
        status = statuses.get(key) or {}
        state = str(status.get("status") or "unknown")
        reason = str(status.get("reason") or "")
        source_id = str(status.get("source_id") or "")
        if state == "ok":
            st.caption(f"{label}：正常（{source_id}）")
        elif state == "unsupported":
            st.caption(f"{label}：{reason or '不支援'}")
        else:
            st.caption(f"{label}：{reason or '暫時失敗'}")


def _snapshot_history(ticker: str) -> pd.DataFrame:
    rows = list_recent_snapshots(ticker, limit=20)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "date" not in df.columns:
        return pd.DataFrame()
    return df.sort_values("date").reset_index(drop=True)


def _historical_institutional_chart(history: pd.DataFrame) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history["date"],
        y=pd.to_numeric(history["institutional_foreign"], errors="coerce"),
        mode="lines+markers",
        name="外資",
        line=dict(color=palette.MORANDI_UP, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=history["date"],
        y=pd.to_numeric(history["institutional_trust"], errors="coerce"),
        mode="lines+markers",
        name="投信",
        line=dict(color=palette.ORANGE, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=history["date"],
        y=pd.to_numeric(history["institutional_dealer"], errors="coerce"),
        mode="lines+markers",
        name="自營商",
        line=dict(color=palette.BROWN, width=2),
    ))
    _apply_chip_layout(fig, "籌碼快照趨勢（張）")
    fig.update_layout(height=260)
    return fig


def _historical_margin_chart(history: pd.DataFrame) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history["date"],
        y=pd.to_numeric(history["margin_balance"], errors="coerce"),
        mode="lines+markers",
        name="融資餘額",
        line=dict(color=palette.BLUE, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=history["date"],
        y=pd.to_numeric(history["short_balance"], errors="coerce"),
        mode="lines+markers",
        name="融券餘額",
        line=dict(color=palette.BROWN, width=1.5),
    ))
    _apply_chip_layout(fig, "籌碼快照趨勢（融資 / 融券）")
    fig.update_layout(height=260)
    return fig


def _render_current_snapshot(institutional: pd.DataFrame, margin: pd.DataFrame, data: dict, *, chart_layout: str = "columns") -> None:
    cols = st.columns(4)
    cols[0].metric("外資", _lots_text(_latest_numeric(institutional, "foreign_net_lots", default=None)))
    cols[1].metric("投信", _lots_text(_latest_numeric(institutional, "investment_trust_net_lots", default=None)))
    margin_balance = _latest_numeric(margin, "margin_balance", default=None)
    cols[2].metric("融資餘額", "—" if margin_balance is None else f"{margin_balance:,.0f}")
    cols[3].metric("外資持股", _pct_text(data.get("qfiis_pct")))
    if institutional.empty and margin.empty:
        st.info("法人與融資券資料暫不可用")
        return
    if institutional.empty:
        st.info("法人買賣超資料暫不可用或不適用")
    if margin.empty:
        st.info("融資券資料暫不可用")
    if not institutional.empty and not margin.empty:
        if chart_layout == "stacked":
            st.plotly_chart(_institutional_flow_chart(institutional), width="stretch")
            st.plotly_chart(_margin_trend_chart(margin), width="stretch")
        else:
            col_flow, col_margin = st.columns([1.4, 1])
            with col_flow:
                st.plotly_chart(_institutional_flow_chart(institutional), width="stretch")
            with col_margin:
                st.plotly_chart(_margin_trend_chart(margin), width="stretch")
    elif not institutional.empty:
        st.plotly_chart(_institutional_flow_chart(institutional), width="stretch")
    elif not margin.empty:
        st.plotly_chart(_margin_trend_chart(margin), width="stretch")


def _institutional_flow_chart(df: pd.DataFrame) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    foreign = pd.to_numeric(df["foreign_net_lots"], errors="coerce").fillna(0)
    investment = pd.to_numeric(df["investment_trust_net_lots"], errors="coerce").fillna(0)
    fig.add_trace(go.Bar(
        x=df["date"],
        y=foreign,
        name="外資",
        marker_color=[palette.MORANDI_UP if value >= 0 else palette.MORANDI_DOWN for value in foreign],
    ))
    fig.add_trace(go.Bar(
        x=df["date"],
        y=investment,
        name="投信",
        marker_color=[palette.MORANDI_UP if value >= 0 else palette.MORANDI_DOWN for value in investment],
    ))
    _apply_chip_layout(fig, "近 5 日法人買賣超（張）")
    fig.update_layout(barmode="group", height=260)
    fig.add_hline(y=0, line_color=palette.BORDER, line_width=1)
    return fig


def _margin_trend_chart(df: pd.DataFrame) -> go.Figure:
    palette = get_chart_palette()
    fig = go.Figure()
    margin_balance = pd.to_numeric(df["margin_balance"], errors="coerce")
    short_balance = pd.to_numeric(df.get("short_balance", pd.Series(dtype=float)), errors="coerce")
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=margin_balance,
        mode="lines+markers",
        name="融資餘額",
        line=dict(color=palette.BLUE, width=2),
    ))
    if short_balance.notna().any():
        fig.add_trace(go.Scatter(
            x=df["date"],
            y=short_balance,
            mode="lines+markers",
            name="融券餘額",
            line=dict(color=palette.BROWN, width=1.5),
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
    palette = get_chart_palette()
    apply_chart_theme(fig, title=title)
    fig.update_layout(
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=palette.BORDER)
    fig.update_yaxes(showgrid=True, gridcolor=palette.BORDER)


def _lots_text(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value or 0)
    if abs(value) >= 10_000:
        return f"{value / 10_000:+.2f}萬張"
    return f"{value:+,.0f}張"


def _pct_delta_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return None


def _pct_text(value: object) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"


def _latest_numeric(df: pd.DataFrame, column: str, default: float | None = 0.0) -> float | None:
    if df.empty or column not in df.columns:
        return default
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return default
    return float(series.iloc[-1])
