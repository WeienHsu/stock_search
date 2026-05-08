from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.index_fetcher import index_snapshot
from src.ui.components.index_mini_chart import build_index_sparkline
from src.ui.nav.page_keys import LABEL_BY_KEY, MARKET


def render_market_full_cards(
    taiex: pd.DataFrame,
    gtsm: pd.DataFrame,
    realtime_breadth: dict | None = None,
) -> None:
    st.markdown("### 台股大盤")
    col1, col2 = st.columns(2)
    with col1:
        render_index_full_card("TAIEX 加權指數", taiex)
    with col2:
        render_index_full_card("GTSM 櫃買指數", gtsm)
    if realtime_breadth:
        render_realtime_breadth_card(realtime_breadth)


def render_market_mini_strip(
    taiex: pd.DataFrame,
    gtsm: pd.DataFrame,
    realtime_breadth: dict | None = None,
) -> None:
    cols = st.columns([1.2, 1.2, 1.6, 0.9])
    render_index_metric(cols[0], "TAIEX", taiex)
    render_index_metric(cols[1], "GTSM", gtsm)
    render_breadth_metric(cols[2], realtime_breadth or {})
    if cols[3].button("大盤總覽", use_container_width=True, key="open_market_overview"):
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[MARKET]
        st.rerun()


def render_index_full_card(title: str, df: pd.DataFrame) -> None:
    snap = index_snapshot(df)
    if not snap:
        st.warning(f"{title} 暫無資料")
        return
    metric_cols = st.columns(4)
    metric_cols[0].metric("收盤", f"{snap['close']:.2f}", f"{snap['change_pct']:.2f}%")
    metric_cols[1].metric("KD", snap["kd_status"])
    metric_cols[2].metric("MACD", snap["macd_status"])
    metric_cols[3].metric("MA 排列", "★" * int(snap["ma_score"]))
    volume_ratio = snap.get("volume_ratio")
    if volume_ratio is not None:
        st.caption(f"成交量 / 5日均量：{volume_ratio:.2f}x")
    st.plotly_chart(build_index_sparkline(df.tail(60), title), use_container_width=True)


def render_index_metric(container, title: str, df: pd.DataFrame) -> None:
    snap = index_snapshot(df)
    if not snap:
        container.metric(title, "—")
        return
    container.metric(title, f"{snap['close']:.2f}", f"{snap['change_pct']:.2f}%")


def render_breadth_metric(container, data: dict) -> None:
    if data.get("available"):
        diff = int(data.get("buy_sell_diff", 0))
        ratio = data.get("ratio")
        delta = f"ratio {float(ratio):.2f}" if ratio is not None else None
        container.metric("即時委買賣差", f"{diff:,.0f}", delta)
        return
    container.metric("即時委買賣差", "—")


def render_realtime_breadth_card(data: dict) -> None:
    st.markdown("#### 即時委買 / 委賣")
    if not data.get("available"):
        st.info(data.get("message", "即時委買委賣資料暫不可用"))
        return
    col_buy, col_sell, col_diff = st.columns(3)
    col_buy.metric("委買張數", f"{int(data.get('buy_orders_lots', 0)):,.0f}")
    col_sell.metric("委賣張數", f"{int(data.get('sell_orders_lots', 0)):,.0f}")
    col_diff.metric("買賣差", f"{int(data.get('buy_sell_diff', 0)):,.0f}")
    ratio = data.get("ratio")
    if ratio is not None:
        st.progress(min(1.0, max(0.0, float(ratio) / 2)), text=f"委買 / 委賣 ratio：{float(ratio):.2f}")
    st.caption(f"最後更新：{data.get('ts') or '—'}")
