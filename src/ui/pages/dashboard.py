import streamlit as st

from src.core.strategy_registry import get as get_strategy
from src.data.news_fetcher import fetch_news
from src.data.price_fetcher import fetch_prices, fetch_prices_for_strategy
from src.data.sentiment_analyzer import analyze_sentiment
from src.data.ticker_utils import normalize_ticker
from src.indicators.bias import add_bias
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.macd import add_macd
from src.strategies.strategy_d import scan_strategy_d, prepare_df
from src.ui.charts.kline_chart import (
    build_bias_chart, build_kd_chart, build_macd_chart, build_main_chart,
)
from src.ui.components.news_card import render_news_section
from src.ui.components.signal_lights import render_signal_badge

import src.strategies.strategy_d  # ensure strategy is registered
import src.strategies.bias_strategy


def render(cfg: dict, user_id: str) -> None:
    ticker = normalize_ticker(cfg["ticker"])

    if not ticker:
        st.info("請在左側輸入股票代號")
        return

    st.markdown(f"## {ticker}")

    # ── Fetch data ──
    with st.spinner(f"載入 {ticker} 資料…"):
        df_display = fetch_prices(ticker, period=cfg["period"])
        df_strategy = fetch_prices_for_strategy(ticker, years=1)

    if df_display.empty:
        st.error(f"無法取得 **{ticker}** 的價格資料，請確認代號是否正確。")
        return

    # ── Compute indicators on display df ──
    sd_params = cfg["strategy_d"]
    df_display = add_ma(df_display, periods=cfg["ma_periods"] or [5, 20, 60])
    df_display = add_macd(df_display,
                          fast=sd_params["macd_fast"],
                          slow=sd_params["macd_slow"],
                          signal=sd_params["macd_signal"])
    df_display = add_kd(df_display,
                        k=sd_params["kd_k"],
                        d=sd_params["kd_d"],
                        smooth_k=sd_params["kd_smooth_k"])
    df_display = add_bias(df_display, period=cfg["bias_period"])

    # ── Strategy D signals (computed on full 1Y history for accuracy) ──
    signal_dates: list[str] = []
    today_signal = False
    if not df_strategy.empty:
        try:
            df_s = prepare_df(df_strategy, sd_params)
            sig_df = scan_strategy_d(
                df_s,
                kd_window=sd_params["kd_window"],
                n_bars=sd_params["n_bars"],
                recovery_pct=sd_params["recovery_pct"],
                kd_k_threshold=sd_params["kd_k_threshold"],
            )
            if not sig_df.empty and "date" in sig_df.columns:
                signal_dates = [str(d)[:10] for d in sig_df["date"]]
                today_signal = signal_dates[-1] == df_strategy["date"].iloc[-1][:10]
        except Exception:
            pass

    # ── Signal badge ──
    render_signal_badge(today_signal)
    st.markdown("")

    # ── Main K-line chart ──
    fig_main = build_main_chart(
        df_display, ticker,
        ma_periods=cfg["ma_periods"],
        signal_dates=signal_dates,
    )
    st.plotly_chart(fig_main, use_container_width=True, config={"displayModeBar": False})

    # ── Sub-panels ──
    if cfg["show_macd"] and "histogram" in df_display.columns:
        st.plotly_chart(build_macd_chart(df_display),
                        use_container_width=True, config={"displayModeBar": False})

    if cfg["show_kd"] and "K" in df_display.columns:
        st.plotly_chart(build_kd_chart(df_display),
                        use_container_width=True, config={"displayModeBar": False})

    if cfg["show_bias"]:
        fig_bias = build_bias_chart(df_display, cfg["bias_period"])
        if fig_bias.data:
            st.plotly_chart(fig_bias,
                            use_container_width=True, config={"displayModeBar": False})

    # ── News & sentiment ──
    if cfg["show_news"]:
        st.markdown("---")
        with st.spinner("載入新聞…"):
            try:
                articles = fetch_news(ticker)
                sentiment = analyze_sentiment(articles)
            except Exception:
                articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
        render_news_section(articles, sentiment)
