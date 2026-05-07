from __future__ import annotations

import pandas as pd
import streamlit as st

from src.core.finnhub_mode import MissingFinnhubKey
from src.data.chip_utils import is_probable_taiwan_etf, is_taiwan_ticker
from src.data.major_holder_fetcher import (
    fetch_major_holder_snapshot,
    holder_history_to_frame,
    holder_snapshot_to_frame,
)
from src.data.news_fetcher import fetch_news
from src.data.revenue_fetcher import fetch_monthly_revenue
from src.data.sentiment_analyzer import analyze_sentiment
from src.repositories.source_health_repo import format_health_summary, get_source_health
from src.sentiment import aggregate_sentiment
from src.ui.components.chip_panel import render_chip_panel
from src.ui.components.intraday_tick_chart import render_intraday_tick_chart
from src.ui.components.news_card import render_news_section
from src.ui.components.sentiment_panel import render_sentiment_panel
from src.ui.components.source_health_badge import render_source_health_badge


def render_stock_detail_tabs(ticker: str, user_id: str) -> None:
    tabs = st.tabs(["技術", "分鐘", "融資券", "月營收", "外資大戶", "新聞"])
    with tabs[0]:
        st.caption("技術面主要整合於左側 K 線與均線/形態/Volume Profile 圖層。")
    with tabs[1]:
        render_intraday_tick_chart(ticker, key=f"stock_detail_intraday_tab_{ticker}")
    with tabs[2]:
        if is_taiwan_ticker(ticker):
            render_chip_panel(ticker)
        else:
            st.info("融資券資料僅支援台股")
    with tabs[3]:
        _render_revenue_tab(ticker)
    with tabs[4]:
        _render_major_holder_tab(ticker)
    with tabs[5]:
        _render_news_tab(ticker, user_id)


def _render_revenue_tab(ticker: str) -> None:
    if not is_taiwan_ticker(ticker):
        st.info("月營收資料僅支援台股")
        return
    if is_probable_taiwan_etf(ticker):
        st.info("此標的為 ETF / 受益憑證（代號以 00 開頭），依規定不公告公司月營收，因此無資料可顯示。")
        st.caption("若要查看 ETF 規模、淨值、持股，請改看其他面板（規劃中）。")
        return
    try:
        df = fetch_monthly_revenue(ticker, months=12)
    except Exception as exc:
        st.info(f"月營收資料暫不可用：{exc}")
        return
    render_source_health_badge("revenue_finmind", "月營收 FinMind")
    render_source_health_badge("revenue_mops", "月營收 MOPS")
    if df.empty:
        st.info("月營收資料暫不可用")
        st.caption(_source_health_text(["revenue_finmind", "revenue_mops"]))
        return
    st.dataframe(df[["period", "revenue", "yoy_pct"]], hide_index=True, use_container_width=True)
    st.line_chart(df, x="period", y="revenue", height=220)


def _render_major_holder_tab(ticker: str) -> None:
    if not is_taiwan_ticker(ticker):
        st.info("外資大戶資料僅支援台股")
        return
    snapshot = fetch_major_holder_snapshot(ticker)
    df = holder_snapshot_to_frame(snapshot)
    render_source_health_badge("major_holder_qfiis", "外資持股")
    if df.empty:
        st.info(snapshot.get("message", "外資持股資料暫不可用"))
        st.caption(_source_health_text(["major_holder_qfiis"]))
        return
    name = snapshot.get("stock_name")
    if name:
        st.caption(f"標的：{name}")
    st.dataframe(df, hide_index=True, use_container_width=True)
    history = holder_history_to_frame(snapshot)
    if not history.empty and len(history) >= 2:
        st.markdown("**外資持股比率趨勢**")
        chart_df = history.rename(columns={"date": "日期", "foreign_holding_pct": "外資持股比率(%)"})
        st.line_chart(chart_df, x="日期", y="外資持股比率(%)", height=220)


def _render_news_tab(ticker: str, user_id: str) -> None:
    try:
        articles = fetch_news(ticker, user_id)
        sentiment = analyze_sentiment(articles)
    except MissingFinnhubKey as exc:
        st.info(f"{exc}（可至設定頁配置）")
        articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
    except Exception as exc:
        st.info(f"新聞資料暫不可用：{exc}")
        articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
    try:
        aggregate = aggregate_sentiment(ticker, articles)
        render_sentiment_panel(aggregate)
    except Exception:
        pass
    render_news_section(articles, sentiment, ticker=ticker, user_id=user_id)


def revenue_frame_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["period", "revenue", "yoy_pct"])
    return df[["period", "revenue", "yoy_pct"]]


def _source_health_text(source_ids: list[str]) -> str:
    summaries = []
    for source_id in source_ids:
        health = get_source_health(source_id)
        summaries.append(f"{source_id}: {format_health_summary(health)}")
    return "；".join(summaries)
