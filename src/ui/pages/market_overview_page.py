from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.index_fetcher import enrich_index_indicators, fetch_index_ohlcv, get_taiex_realtime_breadth
from src.data.market_sentiment_fetcher import fetch_cnn_fear_greed, fetch_mmfi
from src.data.taifex_fetcher import fetch_taifex_txf_open_interest
from src.data.twse_fetcher import fetch_institutional_flow, fetch_margin_summary, fetch_valuation_summary
from src.ui.components.fear_greed_gauge import build_fear_greed_gauge
from src.ui.components.index_mini_chart import build_bar_chart, build_line_chart
from src.ui.components.market_summary import render_market_full_cards
from src.ui.components.source_health_badge import render_source_health_badge


def render() -> None:
    st.markdown("## 大盤總覽")

    with st.spinner("載入大盤資料中..."):
        taiex = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("taiex", "3mo")))
        gtsm = _safe_df(lambda: enrich_index_indicators(fetch_index_ohlcv("gtsm", "3mo")))
        usdtwd = _safe_df(lambda: fetch_index_ohlcv("usdtwd", "1mo"))
        institutional = _safe_df(lambda: fetch_institutional_flow(10))
        taifex = _safe_df(lambda: fetch_taifex_txf_open_interest(10))
        fear_greed = _safe_dict(fetch_cnn_fear_greed)
        mmfi = _safe_dict(fetch_mmfi)
        valuation = _safe_dict(fetch_valuation_summary)
        margin = _safe_dict(fetch_margin_summary)
        realtime_breadth = _safe_dict(get_taiex_realtime_breadth)

    render_market_full_cards(taiex, gtsm, realtime_breadth)
    render_source_health_badge("taiex_realtime", "即時委買賣")
    st.markdown("---")
    _render_flow_and_fx(usdtwd, institutional, taifex)
    st.markdown("---")
    _render_us_sentiment(fear_greed, mmfi)
    st.markdown("---")
    _render_taiwan_valuation(valuation, margin)


def _render_flow_and_fx(usdtwd: pd.DataFrame, institutional: pd.DataFrame, taifex: pd.DataFrame) -> None:
    st.markdown("### 匯率與法人動向")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(build_line_chart(usdtwd.tail(20), "date", "close", "USD/TWD 近 20 日"), use_container_width=True)
    with col2:
        st.plotly_chart(
            build_bar_chart(institutional, "date", "foreign_net_lots", "外資買賣超（上市+上櫃，張）"),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(
            build_bar_chart(institutional, "date", "investment_trust_net_lots", "投信買賣超（上市+上櫃，張）"),
            use_container_width=True,
        )
    with col4:
        if taifex.empty:
            st.info("TAIFEX 外資期貨未平倉資料暫不可用")
        else:
            st.plotly_chart(
                build_bar_chart(taifex, "date", "foreign_oi_net_contracts", "外資臺指期未平倉淨口數"),
                use_container_width=True,
            )


def _render_us_sentiment(fear_greed: dict, mmfi: dict) -> None:
    st.markdown("### 美股情緒")
    col1, col2 = st.columns([1, 1])
    with col1:
        if fear_greed:
            st.plotly_chart(build_fear_greed_gauge(fear_greed), use_container_width=True)
            st.caption(f"更新時間：{fear_greed.get('timestamp', '—')}")
        else:
            st.warning("CNN Fear & Greed 暫不可用")
    with col2:
        if mmfi:
            st.metric("$MMFI 全市場廣度", f"{float(mmfi.get('last_price', 0)):.2f}", help="Barchart Percent of Stocks Above 50-Day Average")
            st.progress(min(100, max(0, int(float(mmfi.get("last_price", 0))))) / 100)
            st.caption(f"交易時間：{mmfi.get('trade_time', '—')}；30/70 可作為情緒轉折區。")
        else:
            st.info("$MMFI 暫不可用")


def _render_taiwan_valuation(valuation: dict, margin: dict) -> None:
    st.markdown("### 台股估值與融資融券")
    col1, col2, col3 = st.columns(3)
    pe = valuation.get("median_pe")
    if pe is None:
        col1.metric("上市個股本益比中位數", "—")
    else:
        col1.metric("上市個股本益比中位數", f"{float(pe):.2f}")
    col2.metric("融資今日餘額合計", f"{float(margin.get('margin_balance', 0)):,.0f}")
    col3.metric("融券今日餘額合計", f"{float(margin.get('short_balance', 0)):,.0f}")
    st.caption("估值使用 TWSE BWIBBU_d 個股資料彙整；融資融券使用 TWSE MI_MARGN 最新資料。")


def _safe_df(loader) -> pd.DataFrame:
    try:
        return loader()
    except Exception as exc:
        st.caption(f"資料載入失敗：{exc}")
        return pd.DataFrame()


def _safe_dict(loader) -> dict:
    try:
        data = loader()
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        st.caption(f"資料載入失敗：{exc}")
        return {}
