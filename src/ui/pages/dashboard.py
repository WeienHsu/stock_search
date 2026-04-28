from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from src.core.finnhub_mode import MissingFinnhubKey
from src.core.strategy_registry import get as get_strategy
from src.data.news_fetcher import fetch_news
from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.sentiment_analyzer import analyze_sentiment
from src.data.ticker_utils import normalize_ticker
from src.indicators.bias import add_bias
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.macd import add_macd
from src.strategies.strategy_d import (
    scan_strategy_d, scan_strategy_d_sell,
    prepare_df, diagnose_strategy_d, diagnose_strategy_d_sell,
)
from src.ui.charts.kline_chart import build_combined_chart
from src.ui.components.news_card import render_news_section
from src.ui.components.signal_lights import render_signal_badge

import src.strategies.strategy_d  # ensure strategy is registered
import src.strategies.bias_strategy

_PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1095, "5Y": 1825}


def render(cfg: dict, user_id: str) -> None:
    ticker = normalize_ticker(cfg["ticker"])

    if not ticker:
        st.info("請在左側輸入股票代號")
        return

    col_title, col_reset = st.columns([9, 1])
    with col_title:
        st.markdown(f"## {ticker}")
    with col_reset:
        st.markdown("<div style='padding-top:0.6rem'></div>", unsafe_allow_html=True)
        if st.button("↩ 重置", key="btn_reset_chart", help="重置縮放至選定期間"):
            st.session_state["chart_nonce"] = st.session_state.get("chart_nonce", 0) + 1
            st.rerun()

    # ── Fetch full 10Y data (always, for indicator warm-up and pan history) ──
    with st.spinner(f"載入 {ticker} 資料…"):
        df_full = fetch_prices_for_strategy(ticker, years=10)

    if df_full.empty:
        st.error(f"無法取得 **{ticker}** 的價格資料，請確認代號是否正確。")
        return

    # ── Compute indicators on full 10Y to avoid short-period row shortage ──
    sd_params = cfg["strategy_d"]
    failed_indicators: list[str] = []

    df_full = add_ma(df_full, periods=cfg["ma_periods"] or [5, 20, 60])

    try:
        df_full = add_macd(df_full,
                           fast=sd_params["macd_fast"],
                           slow=sd_params["macd_slow"],
                           signal=sd_params["macd_signal"])
    except ValueError:
        failed_indicators.append("MACD")

    try:
        df_full = add_kd(df_full,
                         k=sd_params["kd_k"],
                         d=sd_params["kd_d"],
                         smooth_k=sd_params["kd_smooth_k"])
    except ValueError:
        failed_indicators.append("KD")

    try:
        df_full = add_bias(df_full, period=cfg["bias_period"])
    except ValueError:
        failed_indicators.append("Bias")

    # ── Strategy D: buy + sell signals (full 5Y) ──
    buy_dates: list[str] = []
    sell_dates: list[str] = []
    today_buy = False
    today_sell = False
    df_s: pd.DataFrame | None = None
    try:
        df_s = prepare_df(df_full, sd_params)
        buy_df = scan_strategy_d(
            df_s,
            kd_window=sd_params["kd_window"],
            n_bars=sd_params["n_bars"],
            recovery_pct=sd_params["recovery_pct"],
            kd_k_threshold=sd_params["kd_k_threshold"],
        )
        if not buy_df.empty and "date" in buy_df.columns:
            buy_dates = [str(d)[:10] for d in buy_df["date"]]
            today_buy = bool(buy_dates) and buy_dates[-1] == df_full["date"].iloc[-1][:10]

        if sd_params.get("enable_sell_signal", True):
            sell_df = scan_strategy_d_sell(
                df_s,
                kd_window=sd_params["kd_window"],
                n_bars=sd_params["n_bars"],
                recovery_pct=sd_params["recovery_pct"],
                kd_d_threshold=sd_params.get("kd_d_threshold", 80),
            )
            if not sell_df.empty and "date" in sell_df.columns:
                sell_dates = [str(d)[:10] for d in sell_df["date"]]
                today_sell = bool(sell_dates) and sell_dates[-1] == df_full["date"].iloc[-1][:10]
    except Exception:
        pass

    # ── Signal badge ──
    _render_dual_badge(today_buy, today_sell)
    st.markdown("")

    if failed_indicators:
        st.warning(f"⚠️ 資料不足，以下技術指標無法計算：{', '.join(failed_indicators)}")

    # ── Chart window: always show full history; set initial X view to selected period ──
    period = cfg["period"]
    cutoff_days = _PERIOD_DAYS.get(period, 183)
    cutoff_date = (datetime.now() - timedelta(days=cutoff_days)).strftime("%Y-%m-%d")
    _visible = df_full[df_full["date"] >= cutoff_date]
    x_range_start = _visible["date"].iloc[0] if not _visible.empty else df_full["date"].iloc[0]
    df_chart = df_full
    chart_buy_dates = buy_dates
    chart_sell_dates = sell_dates
    nonce = st.session_state.get("chart_nonce", 0)

    fig = build_combined_chart(
        df_chart, ticker,
        ma_periods=cfg["ma_periods"],
        signal_dates=chart_buy_dates,
        sell_dates=chart_sell_dates,
        bias_period=cfg["bias_period"],
        show_macd=cfg["show_macd"] and "histogram" in df_chart.columns,
        show_kd=cfg["show_kd"] and "K" in df_chart.columns,
        show_bias=cfg["show_bias"],
        x_range_start=x_range_start,
        period=period,
        uirevision=f"{ticker}_{period}_{nonce}",
    )
    st.plotly_chart(
        fig, use_container_width=True,
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "toImage"],
        },
        key=f"main_chart_{ticker}",
    )
    st.caption("提示：框選可縮放 X 軸，Y 軸鎖定不跟隨。底部滑桿可查看更早歷史。點擊 ↩ 重置 或圖表右上角「Reset axes」可回到選定期間。")

    # ── Strategy condition diagnosis ──
    st.markdown("---")
    with st.expander("🔍 策略條件診斷", expanded=False):
        if df_s is None:
            st.warning("策略指標計算失敗，無法執行診斷。")
        else:
            col_d, col_type = st.columns([1, 1])
            with col_d:
                latest_date = pd.Timestamp(df_full["date"].iloc[-1]).date()
                diag_date = st.date_input("選擇日期", value=latest_date, key="diag_date")
            with col_type:
                diag_type = st.radio("訊號類型", ["買進", "賣出"], horizontal=True, key="diag_type")

            if st.button("診斷", key="btn_diagnose"):
                date_str = str(diag_date)
                if diag_type == "買進":
                    conditions = diagnose_strategy_d(df_s, date_str, sd_params)
                else:
                    conditions = diagnose_strategy_d_sell(df_s, date_str, sd_params)

                if conditions is None:
                    st.warning(f"日期 {date_str} 不在資料範圍內（僅有最近 10 年資料）")
                else:
                    all_pass = all(c["passed"] for c in conditions)
                    label = "買進" if diag_type == "買進" else "賣出"
                    if all_pass:
                        st.success(f"✅ 所有條件均通過 — {date_str} 有 Strategy D {label}訊號")
                    else:
                        st.error(f"❌ 部分條件未通過 — {date_str} 無 Strategy D {label}訊號")
                    for c in conditions:
                        icon = "✅" if c["passed"] else "❌"
                        st.markdown(f"**{icon} {c['condition']}**")
                        rows = []
                        for m in c.get("metrics", []):
                            actual = m["actual"]
                            target = m.get("target", "—")
                            unit = m.get("unit", "")
                            m_passed = m.get("passed")
                            if "progress" in m and isinstance(actual, (int, float)):
                                ratio = max(0.0, min(1.0, float(m["progress"])))
                                if unit == "%":
                                    bar_text = f"{m['name']}：{actual:.1%} / 需 {m.get('comparison','')} {target:.0%}（已達 {ratio:.0%}）"
                                else:
                                    bar_text = f"{m['name']}：{actual:.2f} / {m.get('comparison','')} {target}（已達 {ratio:.0%}）"
                                st.progress(ratio, text=bar_text)
                            if isinstance(actual, float):
                                actual_str = f"{actual:.1%}" if unit == "%" else f"{actual:.2f}"
                            else:
                                actual_str = str(actual)
                            if isinstance(target, float):
                                target_str = f"{m.get('comparison','')} {target:.1%}".strip() if unit == "%" else f"{m.get('comparison','')} {target:.2f}".strip()
                            else:
                                target_str = f"{m.get('comparison','')} {target}".strip()
                            pass_icon = "✅" if m_passed is True else ("❌" if m_passed is False else "—")
                            rows.append({"項目": m["name"], "目前值": actual_str, "目標": target_str, "通過": pass_icon})
                        if rows:
                            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                        st.caption(c.get("summary", ""))

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


def _render_dual_badge(today_buy: bool, today_sell: bool) -> None:
    """Show buy/sell signal badges side by side."""
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if today_buy:
            st.success("🟢 今日買進訊號")
        else:
            st.info("— 無買進訊號")
    with cols[1]:
        if today_sell:
            st.warning("🔴 今日賣出訊號")
        else:
            st.info("— 無賣出訊號")
