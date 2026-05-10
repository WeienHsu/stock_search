from __future__ import annotations

import streamlit as st

from src.repositories.holdings_repo import get_holdings
from src.risk.holdings_pnl import compute_holdings_pnl
from src.ui.components.empty_state import render_empty_state
from src.ui.components.kpi_card import render_kpi_card


def render_today_holdings_summary(user_id: str) -> None:
    holdings = get_holdings(user_id)
    if not holdings:
        render_empty_state(
            "data",
            "尚未設定持股",
            "請先在「設定 → 持股管理」中輸入持股資料。",
        )
        return

    with st.spinner("計算持股損益…"):
        result = _cached_holdings_pnl(holdings)

    summary = result["summary"]
    items = result["items"]

    col_count, col_value, col_pnl = st.columns(3)
    with col_count:
        render_kpi_card("持股檔數", f"{summary['count']:,}")
    with col_value:
        market_value = summary["market_value"]
        value_label = _money(market_value) if market_value else "—"
        render_kpi_card("持股市值", value_label)
    with col_pnl:
        pnl = summary["unrealized_pnl"]
        pct = summary["unrealized_pnl_pct"]
        if summary["market_value"] == 0.0:
            render_kpi_card("未實現損益", "—", delta="等待報價")
        else:
            direction = "up" if pnl > 0 else "down" if pnl < 0 else "flat"
            render_kpi_card(
                "未實現損益",
                _money(pnl),
                delta=f"{pct:+.2f}%",
                delta_direction=direction,
            )

    unpriced = [i["ticker"] for i in items if i["current_price"] is None]
    if unpriced:
        st.caption(f"⚠ 以下股票目前無法取得報價：{', '.join(unpriced)}")


@st.cache_data(ttl=60, show_spinner=False)
def _cached_holdings_pnl(holdings: list[dict]) -> dict:
    return compute_holdings_pnl(holdings)


def _money(value: float | int) -> str:
    v = float(value)
    prefix = "+" if v > 0 else ""
    return f"{prefix}{v:,.0f}"
