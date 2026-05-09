from __future__ import annotations

from datetime import datetime, time

import pandas as pd
import streamlit as st

import src.strategies.bias_strategy  # ensure registration
import src.strategies.strategy_d  # ensure registration
import src.strategies.strategy_kd  # ensure registration

from src.core.sorting import sort_watchlist_items
from src.core.market_calendar import TAIWAN_TZ
from src.data.dynamic_ttl import get_ttl
from src.data.index_fetcher import enrich_index_indicators, fetch_index_ohlcv, get_taiex_realtime_breadth
from src.repositories.risk_settings_repo import get_risk_settings
from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist
from src.ui.components.empty_state import render_empty_state
from src.ui.components.kpi_card import render_kpi_card
from src.ui.components.market_summary import render_market_mini_strip
from src.ui.components.badge import render_status_pill
from src.ui.components.signal_dot import signal_dot_html
from src.ui.components.today_holdings_summary import render_today_holdings_summary
from src.ui.layout.page_header import Kpi, render_page_header
from src.ui.nav.page_keys import DASHBOARD, LABEL_BY_KEY, SCANNER, SETTINGS, WORKSTATION
from src.ui.utils.format_a11y import format_taipei_datetime


def render(cfg: dict, user_id: str) -> None:
    render_page_header(
        "Today",
        subtitle="大盤概況、自選訊號與持股摘要",
        kpis=_portfolio_kpis(user_id),
    )

    st.markdown("### 大盤概況")
    _render_market_strip_fragment()

    st.divider()
    st.markdown("### 訊號摘要")
    _render_watchlist_signals(cfg, user_id)

    st.divider()
    st.markdown("### 持股摘要")
    render_today_holdings_summary(user_id)

    st.divider()
    st.markdown("### 快速動作")
    _render_quick_actions()


def _portfolio_kpis(user_id: str) -> list[Kpi]:
    risk = get_risk_settings(user_id)
    portfolio_size = float(risk.get("portfolio_size") or 0)
    max_risk_pct = float(risk.get("max_risk_per_trade_pct") or 0)
    return [
        Kpi("持股/資金規模", f"{portfolio_size:,.0f}", help="暫以風控設定中的投資組合規模顯示"),
        Kpi("單筆風險上限", f"{max_risk_pct:.1f}%", help="風控設定中的每筆最大風險比例"),
    ]


@st.fragment(run_every=30)
def _render_market_strip_fragment() -> None:
    with st.spinner("載入大盤概況..."):
        taiex, gtsm, breadth = _market_strip_data()
    render_market_mini_strip(taiex, gtsm, breadth)
    now = datetime.now(TAIWAN_TZ)
    session_label = _tw_market_session_label(now)
    render_status_pill(session_label, _session_pill_kind(session_label))
    st.caption(format_taipei_datetime(now))


@st.cache_data(ttl=get_ttl(30), show_spinner=False)
def _market_strip_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    taiex = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("taiex", "1mo")))
    gtsm = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("gtsm", "1mo")))
    breadth = _safe_dict(get_taiex_realtime_breadth)
    return taiex, gtsm, breadth


@st.cache_data(ttl=get_ttl(300), show_spinner=False)
def _scan_today_watchlist(items: list[dict], strategy_id: str, strategy_params: dict) -> pd.DataFrame:
    return scan_watchlist(items, strategy_id=strategy_id, strategy_params=strategy_params)


def _render_watchlist_signals(cfg: dict, user_id: str) -> None:
    items = sort_watchlist_items(get_watchlist(user_id))
    if not items:
        if render_empty_state(
            "search",
            "自選清單為空",
            "請先新增股票後再查看每日訊號。",
            action_label="前往設定",
            action_key="today_empty_watchlist_settings",
        ):
            st.session_state["_pending_nav_page"] = LABEL_BY_KEY[SETTINGS]
            st.rerun()
        return

    active = cfg.get("active_strategies") or ["strategy_d"]
    strategy_id = active[0]
    strategy_params = cfg.get(strategy_id, {})
    with st.spinner("掃描自選訊號..."):
        result_df = _scan_today_watchlist(items, strategy_id, strategy_params)

    if result_df.empty:
        st.info("目前沒有可顯示的自選訊號")
        return

    _render_signal_counts(result_df)
    table = _today_table(result_df)
    event = st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        key="today_watchlist_signals_table",
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "代號": st.column_config.TextColumn("代號", width="small"),
            "名稱": st.column_config.TextColumn("名稱", width="medium"),
            "現價": st.column_config.NumberColumn("現價", format="%.2f", width="small"),
            "買進": st.column_config.TextColumn("買進", width="medium"),
            "賣出": st.column_config.TextColumn("賣出", width="medium"),
            "MA": st.column_config.ProgressColumn("MA", min_value=0, max_value=4, format="%d/4", width="small"),
            "距 POC": st.column_config.NumberColumn("距 POC", format="%+.1f%%", width="small"),
        },
    )
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        ticker = str(table.iloc[selected_idx]["代號"])
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[DASHBOARD]
        st.session_state["_pending_ticker"] = ticker
        st.rerun()

    st.caption("點選任一列可開啟 Dashboard 查看細節。")


def _render_signal_counts(result_df: pd.DataFrame) -> None:
    counts = _signal_counts(result_df)
    col_buy, col_sell, col_neutral = st.columns(3)
    with col_buy:
        render_kpi_card("買進", str(counts["buy"]), suffix_html=signal_dot_html("buy"))
    with col_sell:
        render_kpi_card("賣出", str(counts["sell"]), suffix_html=signal_dot_html("sell"))
    with col_neutral:
        render_kpi_card("中性", str(counts["neutral"]), suffix_html=signal_dot_html("none"))


def _signal_counts(result_df: pd.DataFrame) -> dict[str, int]:
    buy_series = result_df.get("buy_signal", pd.Series(False, index=result_df.index)).fillna(False).astype(bool)
    sell_series = result_df.get("sell_signal", pd.Series(False, index=result_df.index)).fillna(False).astype(bool)
    buy = int(buy_series.sum())
    sell = int(sell_series.sum())
    neutral = int((~buy_series & ~sell_series).sum())
    return {"buy": buy, "sell": sell, "neutral": neutral}


def _render_quick_actions() -> None:
    col_workstation, col_scanner = st.columns(2)
    if col_workstation.button("開啟綜合看盤", key="today_open_workstation", width="stretch"):
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[WORKSTATION]
        st.rerun()
    if col_scanner.button("開啟掃描器", key="today_open_scanner", width="stretch"):
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[SCANNER]
        st.rerun()


def _today_table(result_df: pd.DataFrame) -> pd.DataFrame:
    df = result_df.copy()
    df["__priority"] = df["buy_signal"].astype(int) + df["sell_signal"].astype(int)
    df = df.sort_values(["__priority", "ma_bullish_score", "ticker"], ascending=[False, False, True])
    return pd.DataFrame({
        "代號": df["ticker"].astype(str),
        "名稱": df["name"].astype(str),
        "現價": pd.to_numeric(df["current_close"], errors="coerce"),
        "買進": df["buy_status"].astype(str),
        "賣出": df["sell_status"].astype(str),
        "MA": pd.to_numeric(df["ma_bullish_score"], errors="coerce").fillna(0).astype(int),
        "距 POC": pd.to_numeric(df["poc_distance_pct"], errors="coerce"),
    })


def _safe_df(loader) -> pd.DataFrame:
    try:
        return loader()
    except Exception:
        return pd.DataFrame()


def _safe_dict(loader) -> dict:
    try:
        data = loader()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _tw_market_session_label(now: datetime) -> str:
    if now.weekday() >= 5:
        return "休市"
    current_time = now.time()
    if time(9, 0) <= current_time <= time(13, 30):
        return "盤中"
    if current_time > time(13, 30):
        return "盤後"
    return "盤前"


def _session_pill_kind(label: str) -> str:
    if label == "盤中":
        return "buy"
    if label == "休市":
        return "neutral"
    return "info"
