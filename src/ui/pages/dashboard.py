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
from src.strategies.strategy_d import scan_strategy_d, prepare_df, diagnose_strategy_d
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
        df_strategy = fetch_prices_for_strategy(ticker, years=5)

    if df_strategy.empty:
        st.error(f"無法取得 **{ticker}** 的價格資料，請確認代號是否正確。")
        return

    # ── Compute indicators on full 5Y data to avoid short-period row shortage ──
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

    # Initial x-axis visible range derived from selected quick-zoom period
    _PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1095, "5Y": 1825}
    _cutoff = (datetime.now() - timedelta(days=_PERIOD_DAYS.get(cfg["period"], 183))).strftime("%Y-%m-%d")
    _visible = df_strategy[df_strategy["date"] >= _cutoff]
    x_range_start: str | None = _visible["date"].iloc[0] if not _visible.empty else df_strategy["date"].iloc[0]

    # ── Strategy D signals (full 5Y) ──
    signal_dates: list[str] = []
    today_signal = False
    df_s: pd.DataFrame | None = None
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

    if failed_indicators:
        st.warning(f"⚠️ 資料不足，以下技術指標無法計算：{', '.join(failed_indicators)}")

    # ── Combined chart: full 5Y data with rangeslider; initial view = selected quick-zoom period ──
    fig = build_combined_chart(
        df_strategy, ticker,
        ma_periods=cfg["ma_periods"],
        signal_dates=signal_dates,
        bias_period=cfg["bias_period"],
        show_macd=cfg["show_macd"] and "histogram" in df_strategy.columns,
        show_kd=cfg["show_kd"] and "K" in df_strategy.columns,
        show_bias=cfg["show_bias"],
        x_range_start=x_range_start,
        period=cfg["period"],
    )
    st.plotly_chart(
        fig, use_container_width=True,
        config={"displayModeBar": False},
        key=f"main_chart_{ticker}",
    )
    st.caption("提示：使用底部滾動條可查看更早歷史；拖曳 X 軸可縮放，各面板同步移動")

    # ── Strategy condition diagnosis ──
    st.markdown("---")
    with st.expander("🔍 策略條件診斷", expanded=False):
        if df_s is None:
            st.warning("策略指標計算失敗，無法執行診斷。")
        else:
            col_d, col_s = st.columns([1, 1])
            with col_d:
                latest_date = pd.Timestamp(df_strategy["date"].iloc[-1]).date()
                diag_date = st.date_input("選擇日期", value=latest_date, key="diag_date")
            with col_s:
                st.selectbox("策略", ["Strategy D"], key="diag_strategy")

            if st.button("診斷", key="btn_diagnose"):
                date_str = str(diag_date)
                conditions = diagnose_strategy_d(df_s, date_str, sd_params)
                if conditions is None:
                    st.warning(f"日期 {date_str} 不在資料範圍內（僅有最近 5 年資料）")
                else:
                    all_pass = all(c["passed"] for c in conditions)
                    if all_pass:
                        st.success(f"✅ 所有條件均通過 — {date_str} 有 Strategy D 訊號")
                    else:
                        st.error(f"❌ 部分條件未通過 — {date_str} 無 Strategy D 訊號")
                    for c in conditions:
                        icon = "✅" if c["passed"] else "❌"
                        st.markdown(f"**{icon} {c['condition']}**")
                        rows = []
                        for m in c.get("metrics", []):
                            actual = m["actual"]
                            target = m.get("target", "—")
                            unit = m.get("unit", "")
                            m_passed = m.get("passed")
                            # Progress bar for numeric metrics
                            if "progress" in m and isinstance(actual, (int, float)):
                                ratio = max(0.0, min(1.0, float(m["progress"])))
                                if unit == "%":
                                    bar_text = f"{m['name']}：{actual:.1%} / 需 {m.get('comparison','')} {target:.0%}（已達 {ratio:.0%}）"
                                else:
                                    bar_text = f"{m['name']}：{actual:.2f} / {m.get('comparison','')} {target}（已達 {ratio:.0%}）"
                                st.progress(ratio, text=bar_text)
                            # Build table row
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
