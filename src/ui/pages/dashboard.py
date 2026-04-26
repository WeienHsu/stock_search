import streamlit as st

from src.core.finnhub_mode import MissingFinnhubKey
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
from src.ui.charts.kline_chart import build_combined_chart
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

    # ── Compute indicators on full 1Y data to avoid short-period row shortage ──
    # df_strategy has 1Y of data (enough for MACD/KD warmup), then we trim for display.
    sd_params = cfg["strategy_d"]
    failed_indicators: list[str] = []

    df_strategy = add_ma(df_strategy, periods=cfg["ma_periods"] or [5, 20, 60])

    try:
        df_strategy = add_macd(df_strategy,
                               fast=sd_params["macd_fast"],
                               slow=sd_params["macd_slow"],
                               signal=sd_params["macd_signal"])
    except ValueError:
        failed_indicators.append("MACD")

    try:
        df_strategy = add_kd(df_strategy,
                             k=sd_params["kd_k"],
                             d=sd_params["kd_d"],
                             smooth_k=sd_params["kd_smooth_k"])
    except ValueError:
        failed_indicators.append("KD")

    try:
        df_strategy = add_bias(df_strategy, period=cfg["bias_period"])
    except ValueError:
        failed_indicators.append("Bias")

    # Trim to display period for charting (keeps indicator-computed columns)
    cutoff = df_display["date"].iloc[0]
    df_chart = df_strategy[df_strategy["date"] >= cutoff].copy()

    # ── Strategy D signals (full 1Y history; prepare_df safely recomputes MACD/KD) ──
    signal_dates: list[str] = []
    today_signal = False
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

    # Warn if any indicators still couldn't be computed (very new stocks < 35 days)
    if failed_indicators:
        st.warning(f"⚠️ 資料不足，以下技術指標無法計算：{', '.join(failed_indicators)}")

    # ── Combined chart (shared X-axis — 拖曳縮放時各面板同步) ──
    fig = build_combined_chart(
        df_chart, ticker,
        ma_periods=cfg["ma_periods"],
        signal_dates=signal_dates,
        bias_period=cfg["bias_period"],
        show_macd=cfg["show_macd"] and "histogram" in df_chart.columns,
        show_kd=cfg["show_kd"] and "K" in df_chart.columns,
        show_bias=cfg["show_bias"],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("提示：拖曳 X 軸可縮放，各面板會同步移動")

    # ── News & sentiment ──
    if cfg["show_news"]:
        st.markdown("---")
        with st.spinner("載入新聞…"):
            try:
                articles = fetch_news(ticker, user_id)
                sentiment = analyze_sentiment(articles)
            except MissingFinnhubKey as e:
                st.info(f"💡 {e}（可至⚙️ 設定頁配置）")
                articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
            except Exception:
                articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
        render_news_section(articles, sentiment)
