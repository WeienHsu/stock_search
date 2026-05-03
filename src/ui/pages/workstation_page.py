from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.index_fetcher import (
    enrich_index_indicators,
    fetch_index_ohlcv,
    get_taiex_realtime_breadth,
    index_snapshot,
)
from src.data.price_fetcher import fetch_prices_by_interval
from src.indicators.bias import add_bias
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.ma_analysis import DEFAULT_MA_PERIODS, ma_cross_signal
from src.indicators.macd import add_macd
from src.ui.charts.kline_chart import build_combined_chart, render_combined_chart
from src.ui.components.categorized_watchlist import render_categorized_watchlist
from src.ui.components.intraday_tick_chart import render_intraday_tick_chart
from src.ui.components.stock_detail_tabs import render_stock_detail_tabs


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 綜合看盤")

    default_ticker = str(cfg.get("ticker") or "2330.TW").upper()
    if "workstation_active_ticker" not in st.session_state:
        st.session_state["workstation_active_ticker"] = default_ticker

    left, right = st.columns([1, 1], gap="medium")

    with left:
        with st.container():
            st.markdown("### 分類自選")
            selected = render_categorized_watchlist(user_id)
            if selected:
                st.session_state["workstation_active_ticker"] = selected

        ticker = str(st.session_state.get("workstation_active_ticker") or default_ticker).upper()
        with st.container():
            st.markdown(f"### {ticker} K 線")
            _render_workstation_kline(ticker)

    with right:
        with st.container():
            st.markdown("### 大盤即時看板")
            _render_market_board()

        ticker = str(st.session_state.get("workstation_active_ticker") or default_ticker).upper()
        with st.container():
            st.markdown(f"### {ticker} 分時 / 詳細")
            render_intraday_tick_chart(ticker, key=f"workstation_intraday_top_{ticker}")
            _render_l2_placeholder()
            render_stock_detail_tabs(ticker, user_id)


def _render_workstation_kline(ticker: str) -> None:
    granularity_options = {
        "1m": "1分",
        "5m": "5分",
        "15m": "15分",
        "30m": "30分",
        "60m": "60分",
        "1d": "日",
        "1wk": "週",
        "1mo": "月",
    }
    granularity = st.radio(
        "週期",
        options=list(granularity_options.keys()),
        horizontal=True,
        format_func=lambda value: granularity_options[value],
        key=f"workstation_granularity_{ticker}",
    )
    try:
        df = fetch_prices_by_interval(ticker, granularity, period="6M")
    except Exception as exc:
        st.info(f"K 線資料暫不可用：{exc}")
        return
    if df.empty:
        st.info("K 線資料暫不可用")
        return

    df = _enrich_chart_df(df)
    fig = build_combined_chart(
        df,
        ticker,
        ma_periods=DEFAULT_MA_PERIODS,
        signal_dates=[],
        sell_dates=[],
        bias_period=20,
        show_macd="histogram" in df.columns,
        show_kd="K" in df.columns,
        show_bias=False,
        signal_layers=[],
        show_candlestick_patterns=True,
        show_volume_profile=True,
        ma_cross_events=_recent_cross_events(df),
        granularity=granularity,
        uirevision=f"workstation_{ticker}_{granularity}",
    )
    render_combined_chart(
        fig,
        df,
        key=f"workstation_chart_{ticker}_{granularity}",
        config={"displayModeBar": True, "displaylogo": False},
    )


def _enrich_chart_df(df: pd.DataFrame) -> pd.DataFrame:
    enriched = add_ma(df, DEFAULT_MA_PERIODS)
    try:
        enriched = add_macd(enriched)
    except ValueError:
        pass
    try:
        enriched = add_kd(enriched)
    except ValueError:
        pass
    try:
        enriched = add_bias(enriched, 20)
    except ValueError:
        pass
    return enriched


def _recent_cross_events(df: pd.DataFrame) -> list[dict]:
    events = []
    for fast, slow in [(5, 10), (10, 20), (20, 60), (60, 120), (120, 240)]:
        events.extend(ma_cross_signal(df, fast, slow)[-2:])
    return sorted(events, key=lambda item: item["date"])[-5:]


def _render_market_board() -> None:
    taiex = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("taiex", "1mo")))
    gtsm = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("gtsm", "1mo")))
    breadth = _safe_dict(get_taiex_realtime_breadth)
    col1, col2 = st.columns(2)
    _render_index_metric(col1, "TAIEX", taiex)
    _render_index_metric(col2, "GTSM", gtsm)
    if breadth.get("available"):
        c1, c2, c3 = st.columns(3)
        c1.metric("委買", f"{int(breadth.get('buy_orders_lots', 0)):,.0f}")
        c2.metric("委賣", f"{int(breadth.get('sell_orders_lots', 0)):,.0f}")
        c3.metric("買賣差", f"{int(breadth.get('buy_sell_diff', 0)):,.0f}")
    else:
        st.caption(breadth.get("message", "即時委買委賣資料暫不可用"))


def _render_index_metric(container, title: str, df: pd.DataFrame) -> None:
    snap = index_snapshot(df)
    if not snap:
        container.metric(title, "—")
        return
    container.metric(title, f"{snap['close']:.2f}", f"{snap['change_pct']:.2f}%")


def _render_l2_placeholder() -> None:
    with st.expander("五檔買賣盤 / 內外盤", expanded=False):
        st.info("五檔買賣盤、逐筆成交與內外盤比需要付費即時資料源；目前保留欄位，不以延遲資料冒充 L2。")


def _safe_df(loader) -> pd.DataFrame:
    try:
        return loader()
    except Exception:
        return pd.DataFrame()


def _safe_dict(loader) -> dict:
    try:
        value = loader()
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}
