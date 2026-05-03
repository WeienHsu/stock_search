from __future__ import annotations

import pandas as pd
import streamlit as st

from src.core.finnhub_mode import MissingFinnhubKey
from src.data.chip_fetcher import is_taiwan_ticker
from src.data.major_holder_fetcher import fetch_major_holder_snapshot, holder_snapshot_to_frame
from src.data.news_fetcher import fetch_news
from src.data.revenue_fetcher import fetch_monthly_revenue
from src.data.sentiment_analyzer import analyze_sentiment
from src.ui.components.chip_panel import render_chip_panel
from src.ui.components.intraday_tick_chart import render_intraday_tick_chart
from src.ui.components.news_card import render_news_section


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
    try:
        df = fetch_monthly_revenue(ticker, months=12)
    except Exception as exc:
        st.info(f"月營收資料暫不可用：{exc}")
        return
    if df.empty:
        st.info("月營收資料暫不可用")
        return
    st.dataframe(df[["period", "revenue", "yoy_pct"]], hide_index=True, use_container_width=True)
    st.line_chart(df, x="period", y="revenue", height=220)


def _render_major_holder_tab(ticker: str) -> None:
    if not is_taiwan_ticker(ticker):
        st.info("外資大戶資料僅支援台股")
        return
    snapshot = fetch_major_holder_snapshot(ticker)
    df = holder_snapshot_to_frame(snapshot)
    if df.empty:
        st.info(snapshot.get("message", "外資持股資料暫不可用"))
        return
    st.dataframe(df, hide_index=True, use_container_width=True)


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
    render_news_section(articles, sentiment, ticker=ticker, user_id=user_id)


def revenue_frame_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["period", "revenue", "yoy_pct"])
    return df[["period", "revenue", "yoy_pct"]]
