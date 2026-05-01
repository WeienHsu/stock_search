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
from src.strategies.strategy_d import prepare_df, diagnose_strategy_d, diagnose_strategy_d_sell
from src.ui.charts.kline_chart import build_combined_chart, render_combined_chart, SignalLayer
from src.ui.components.news_card import render_news_section

import src.strategies.strategy_d   # ensure registration
import src.strategies.strategy_kd  # ensure registration
import src.strategies.bias_strategy

_PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1095, "5Y": 1825}

# Per-strategy marker colors (Morandi palette)
_LAYER_COLORS = {
    "strategy_d":  {"buy": "#C8A86A", "sell": "#5B7FA8"},
    "strategy_kd": {"buy": "#6A9E8A", "sell": "#C87D6A"},
    "bias":        {"buy": "#9B8BB4", "sell": "#A89070"},  # purple / brown
}
# Per-strategy glyph distinction: D uses solid triangles, KD uses hollow, Bias uses diamonds
_LAYER_GLYPHS = {
    "strategy_d":  {"buy": "▼", "sell": "▲"},
    "strategy_kd": {"buy": "▽", "sell": "△"},
    "bias":        {"buy": "◆", "sell": "◇"},
}
_STRATEGY_LABELS = {
    "strategy_d":  "Strategy D",
    "strategy_kd": "Strategy KD",
    "bias":        "Bias",
}


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

    # ── Compute signals for each active strategy ──
    active_strategies: list[str] = cfg.get("active_strategies", ["strategy_d"])
    today_str = df_full["date"].iloc[-1][:10]
    today_buy = False
    today_sell = False
    signal_layers: list[SignalLayer] = []
    df_s: pd.DataFrame | None = None  # Strategy D diagnose dataframe

    for strategy_id in active_strategies:
        try:
            params = cfg.get(strategy_id, {})
            signals = get_strategy(strategy_id).compute(df_full, params)
            buy_dates = [s.date for s in signals if s.signal_type == "buy"]
            sell_dates = [s.date for s in signals if s.signal_type == "sell"]

            if any(d == today_str for d in buy_dates):
                today_buy = True
            if any(d == today_str for d in sell_dates):
                today_sell = True

            colors = _LAYER_COLORS.get(strategy_id, {"buy": "#C8A86A", "sell": "#5B7FA8"})
            glyphs = _LAYER_GLYPHS.get(strategy_id, {"buy": "▼", "sell": "▲"})
            signal_layers.append(SignalLayer(
                strategy_id=strategy_id,
                label=_STRATEGY_LABELS.get(strategy_id, strategy_id),
                buy_dates=buy_dates,
                sell_dates=sell_dates,
                buy_color=colors["buy"],
                sell_color=colors["sell"],
                buy_glyph=glyphs["buy"],
                sell_glyph=glyphs["sell"],
            ))

            # Build Strategy D diagnose dataframe (only needed for that strategy)
            if strategy_id == "strategy_d" and df_s is None:
                try:
                    df_s = prepare_df(df_full, sd_params)
                except Exception:
                    pass
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
    nonce = st.session_state.get("chart_nonce", 0)

    fig = build_combined_chart(
        df_full, ticker,
        ma_periods=cfg["ma_periods"],
        signal_dates=[],   # legacy param — signal_layers takes over
        sell_dates=[],
        bias_period=cfg["bias_period"],
        show_macd=cfg["show_macd"] and "histogram" in df_full.columns,
        show_kd=cfg["show_kd"] and "K" in df_full.columns,
        show_bias=cfg["show_bias"],
        x_range_start=x_range_start,
        period=period,
        uirevision=f"{ticker}_{period}_{nonce}",
        signal_layers=signal_layers,
    )
    render_combined_chart(
        fig,
        df_full,
        key=f"main_chart_{ticker}",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "toImage"],
        },
    )
    st.caption("提示：框選可縮放 X 軸，平移或縮放後價格 Y 軸會依可視範圍自動調整。底部滑桿可查看更早歷史。點擊 ↩ 重置 或圖表右上角「Reset axes」可回到選定期間。")

    # ── Strategy D condition diagnosis (Strategy D-specific, shown only when active) ──
    if "strategy_d" in active_strategies:
        st.markdown("---")
        with st.expander("🔍 Strategy D 條件診斷", expanded=False):
            if df_s is None:
                st.warning("Strategy D 指標計算失敗，無法執行診斷。")
            else:
                col_d, col_type = st.columns([1, 1])
                with col_d:
                    latest_date = pd.Timestamp(df_full["date"].iloc[-1]).date()
                    diag_date = st.date_input("選擇日期", value=latest_date, key="diag_date")
                with col_type:
                    diag_type = st.radio("訊號類型", ["買進", "賣出"], horizontal=True, key="diag_type")

                st.caption(_strategy_d_diag_param_summary(sd_params, diag_type))

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


def _strategy_d_diag_param_summary(params: dict, diag_type: str) -> str:
    if diag_type == "買進":
        kd_window = params.get("buy_kd_window", params.get("kd_window", 3))
        n_bars = params.get("buy_n_bars", params.get("n_bars", 3))
        recovery = params.get("buy_recovery_pct", params.get("recovery_pct", 0.6))
        threshold = params.get("buy_kd_k_threshold", params.get("kd_k_threshold", 22))
        max_violations = params.get("buy_max_violations", params.get("max_violations", 1))
        lookback = params.get("buy_lookback_bars", params.get("lookback_bars", 20))
        return (
            f"目前買進設定：KD 回看 {kd_window} 根，交叉當日 K < {threshold}；"
            f"MACD 最近 {n_bars} 根收斂，回看 {lookback} 根峰谷，"
            f"回彈 ≥ {float(recovery):.0%}，容忍違反 {max_violations} 根。"
        )

    kd_window = params.get("sell_kd_window", params.get("kd_window", 3))
    n_bars = params.get("sell_n_bars", params.get("n_bars", 3))
    recovery = params.get("sell_recovery_pct", params.get("recovery_pct", 0.6))
    threshold = params.get("sell_kd_d_threshold", params.get("kd_d_threshold", 80))
    max_violations = params.get("sell_max_violations", params.get("max_violations", 1))
    lookback = params.get("sell_lookback_bars", params.get("lookback_bars", 20))
    return (
        f"目前賣出設定：KD 回看 {kd_window} 根，交叉當日 K > {threshold}；"
        f"MACD 最近 {n_bars} 根收斂，回看 {lookback} 根峰谷，"
        f"回落 ≥ {float(recovery):.0%}，容忍違反 {max_violations} 根。"
    )
