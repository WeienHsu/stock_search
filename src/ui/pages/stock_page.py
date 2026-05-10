from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from src.core.finnhub_mode import MissingFinnhubKey
from src.core.strategy_registry import get as get_strategy
from src.ai.prompts.signal_explainer import generate_signal_explanation
from src.ai.provider_chain import build_default_chain
from src.ai.providers.base import AIProviderError, MissingAIProviderConfig
from src.data.news_fetcher import fetch_news
from src.data.price_fetcher import fetch_prices_by_interval, fetch_prices_for_strategy
from src.data.sentiment_analyzer import analyze_sentiment
from src.data.ticker_utils import normalize_ticker
from src.indicators.bias import add_bias
from src.indicators.kd import add_kd
from src.indicators.ma import add_ma
from src.indicators.ma_analysis import DEFAULT_MA_PERIODS, ma_cross_signal, summarize_ma_state
from src.indicators.macd import add_macd
from src.analysis.trend_detector import detect_hh_hl, detect_neckline, trend_label
from src.indicators.volume_profile_context import summarize_vp_context
from src.strategies.strategy_d import prepare_df, diagnose_strategy_d, diagnose_strategy_d_sell
from src.ui.charts.kline_chart import build_combined_chart, render_combined_chart, SignalLayer
from src.ui.components.integrated_signal_panel import render_integrated_signal
from src.ui.components.chip_panel import render_chip_panel
from src.ui.components.empty_state import render_empty_state
from src.ui.components.news_card import render_news_section
from src.ui.components.sentiment_panel import render_sentiment_panel
from src.ui.layout.page_header import Action, Kpi, render_page_header
from src.ui.nav.page_keys import LABEL_BY_KEY, MARKET, WORKSTATION
from src.ui.theme.plotly_template import get_chart_palette
from src.ui.utils.ticker_display import resolved_display_ticker, should_sync_display_ticker
from src.sentiment import aggregate_sentiment

import src.strategies.strategy_d   # ensure registration
import src.strategies.strategy_kd  # ensure registration
import src.strategies.bias_strategy

_PERIOD_DAYS = {"1M": 31, "3M": 92, "6M": 183, "1Y": 365, "3Y": 1095, "5Y": 1825}

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


def _layer_colors() -> dict[str, dict[str, str]]:
    palette = get_chart_palette()
    return {
        "strategy_d": {"buy": palette.ORANGE, "sell": palette.BLUE},
        "strategy_kd": {"buy": palette.MORANDI_UP, "sell": palette.PURPLE},
        "bias": {"buy": palette.PURPLE, "sell": palette.BROWN},
    }


def render(cfg: dict, user_id: str) -> None:
    ticker = normalize_ticker(cfg["ticker"])

    if not ticker:
        st.info("請在左側輸入股票代號")
        return

    def _goto_workstation() -> None:
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[WORKSTATION]
        st.session_state["_pending_ticker"] = ticker
        st.rerun()

    def _goto_market() -> None:
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[MARKET]
        st.rerun()

    def _reset_chart() -> None:
        st.session_state["chart_nonce"] = st.session_state.get("chart_nonce", 0) + 1
        st.rerun()

    # ── Fetch full 10Y data (always, for indicator warm-up and pan history) ──
    with st.spinner(f"載入 {ticker} 資料…"):
        df_full = fetch_prices_for_strategy(ticker, years=10)

    if df_full.empty:
        render_empty_state("chart", "無法取得價格資料", f"請確認 {ticker} 代號是否正確，或稍後再試。")
        return

    display_ticker = resolved_display_ticker(ticker)
    if should_sync_display_ticker(ticker, display_ticker):
        st.session_state["_resolved_sidebar_ticker"] = display_ticker
        st.session_state["_pending_ticker"] = display_ticker
        st.rerun()
    ticker = display_ticker

    # ── Compute indicators on full 10Y to avoid short-period row shortage ──
    sd_params = cfg["strategy_d"]
    failed_indicators: list[str] = []

    chart_ma_periods = cfg["ma_periods"] or [5, 20, 60]
    analysis_ma_periods = sorted(set(chart_ma_periods + DEFAULT_MA_PERIODS))
    df_full = add_ma(df_full, periods=analysis_ma_periods)

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
    layer_colors = _layer_colors()
    default_palette = get_chart_palette()

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

            colors = layer_colors.get(strategy_id, {"buy": default_palette.GOLD, "sell": default_palette.SIGNAL_SELL})
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

    # ── Compute shared context for integrated panel ──
    vp_ctx: dict | None = None
    try:
        vp_ctx = summarize_vp_context(df_full)
    except Exception:
        pass

    ma_summary = _get_ma_summary(df_full)

    render_page_header(
        title=ticker,
        kpis=_stock_header_kpis(df_full, ma_summary, vp_ctx, today_buy, today_sell),
        actions=[
            Action("綜合看盤", on_click=_goto_workstation, key="btn_dashboard_to_workstation"),
            Action("大盤總覽", on_click=_goto_market, key="btn_dashboard_to_market"),
            Action("↩ 重置", on_click=_reset_chart, key="btn_reset_chart", type="ghost", help="重置縮放至選定期間"),
        ],
    )

    if failed_indicators:
        st.warning(f"⚠️ 資料不足，以下技術指標無法計算：{', '.join(failed_indicators)}")

    _render_kline_fragment(
        ticker=ticker,
        df_full=df_full,
        analysis_ma_periods=analysis_ma_periods,
        chart_ma_periods=chart_ma_periods,
        sd_params=sd_params,
        cfg=cfg,
        signal_layers=signal_layers,
    )

    tab_signal, tab_ma, tab_chip, tab_diag, tab_tv = st.tabs(
        ["訊號判讀", "均線分析", "籌碼", "條件診斷", "進階圖表"]
    )
    with tab_signal:
        render_integrated_signal(df_full, ma_summary, signal_layers, vp_ctx, use_expander=False)
    with tab_ma:
        _render_ma_analysis_content(df_full)
    with tab_chip:
        render_chip_panel(ticker, use_expander=False)
    with tab_diag:
        if "strategy_d" in active_strategies:
            _render_strategy_d_diagnosis(df_full, df_s, sd_params, vp_ctx)
        else:
            st.caption("Strategy D 未啟用")
    with tab_tv:
        from src.ui.components.tradingview_chart import render_tradingview_chart
        render_tradingview_chart(ticker)

    with st.expander("AI 解讀", expanded=False):
        _render_ai_signal_explainer(
            ticker,
            user_id,
            df_full,
            signal_layers,
            today_buy,
            today_sell,
            result_in_expander=False,
        )

    # ── News & sentiment ──
    if cfg["show_news"]:
        st.divider()
        with st.spinner("載入新聞…"):
            try:
                articles = fetch_news(ticker, user_id)
                sentiment = analyze_sentiment(articles)
            except MissingFinnhubKey as e:
                st.info(f"💡 {e}（可至⚙️ 設定頁配置）")
                articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
            except Exception:
                articles, sentiment = [], {"score": 0.0, "label": "neutral", "article_count": 0}
        try:
            aggregate = aggregate_sentiment(ticker, articles)
            render_sentiment_panel(aggregate)
        except Exception:
            st.info("跨來源情緒資料暫不可用")
        render_news_section(articles, sentiment, ticker=ticker, user_id=user_id)


def _render_dual_badge(today_buy: bool, today_sell: bool) -> None:
    """Show buy/sell signal badges side by side."""
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if today_buy:
            st.html('<span class="signal-buy" role="status" aria-label="今日買進訊號">▲ 今日買進訊號</span>')
        else:
            st.info("— 無買進訊號")
    with cols[1]:
        if today_sell:
            st.html('<span class="signal-sell" role="status" aria-label="今日賣出訊號">▼ 今日賣出訊號</span>')
        else:
            st.info("— 無賣出訊號")


def _stock_header_kpis(
    df_full: pd.DataFrame,
    ma_summary: dict,
    vp_ctx: dict | None,
    today_buy: bool,
    today_sell: bool,
) -> list[Kpi]:
    close = pd.to_numeric(df_full["close"], errors="coerce").dropna()
    current = float(close.iloc[-1]) if not close.empty else 0.0
    previous = float(close.iloc[-2]) if len(close) >= 2 else current
    pct_change = ((current - previous) / previous * 100) if previous else 0.0
    direction = "up" if pct_change > 0 else "down" if pct_change < 0 else "flat"

    if today_buy and today_sell:
        signal_label = "買進 / 賣出"
    elif today_buy:
        signal_label = "買進"
    elif today_sell:
        signal_label = "賣出"
    else:
        signal_label = "—"

    poc_dist = vp_ctx.get("poc_distance_pct") if vp_ctx else None
    poc_text = "—" if poc_dist is None else f"{float(poc_dist):+.2f}%"
    ma_score = ma_summary.get("score", 0)

    return [
        Kpi(
            "現價",
            f"{current:.2f}",
            f"{pct_change:+.2f}%",
            delta_direction=direction,
            help="最近收盤價與前一筆收盤價的變化",
            aria_label=f"現價 {current:.2f}，漲跌 {pct_change:+.2f}%",
        ),
        Kpi("今日訊號", signal_label, help="目前啟用策略的當日買賣訊號"),
        Kpi("MA 分數", f"{ma_score}/4", help="MA5/20/60/120 多頭排列達成數"),
        Kpi("距 POC", poc_text, help="當前價對成交量加權中軸的偏離"),
    ]


@st.fragment
def _render_kline_fragment(
    ticker: str,
    df_full: pd.DataFrame,
    analysis_ma_periods: list[int],
    chart_ma_periods: list[int],
    sd_params: dict,
    cfg: dict,
    signal_layers: list[SignalLayer],
) -> None:
    period = cfg["period"]
    cutoff_days = _PERIOD_DAYS.get(period, 183)
    cutoff_date = (datetime.now() - timedelta(days=cutoff_days)).strftime("%Y-%m-%d")
    visible = df_full[df_full["date"] >= cutoff_date]
    x_range_start = visible["date"].iloc[0] if not visible.empty else df_full["date"].iloc[0]
    nonce = st.session_state.get("chart_nonce", 0)
    granularity = cfg.get("kline_granularity", "1d")

    chart_df = _chart_dataframe(ticker, period, granularity, df_full, analysis_ma_periods, sd_params, cfg)
    chart_signal_layers = signal_layers if granularity == "1d" else []
    indicator_flags = _chart_indicator_flags(cfg, chart_df)

    fig = build_combined_chart(
        chart_df,
        ticker,
        ma_periods=chart_ma_periods,
        signal_dates=[],
        sell_dates=[],
        bias_period=cfg["bias_period"],
        show_macd=indicator_flags["show_macd"],
        show_kd=indicator_flags["show_kd"],
        show_bias=indicator_flags["show_bias"],
        x_range_start=x_range_start,
        period=period,
        uirevision=f"{ticker}_{period}_{nonce}",
        signal_layers=chart_signal_layers,
        show_signals=True,
        show_candlestick_patterns=indicator_flags["show_candlestick_patterns"],
        show_volume_profile=indicator_flags["show_volume_profile"],
        show_volume_bar=indicator_flags["show_volume_bar"],
        ma_cross_events=_recent_ma_cross_events(chart_df) if indicator_flags["show_ma_cross_labels"] else [],
        granularity=granularity,
    )
    render_combined_chart(
        fig,
        chart_df,
        key=f"main_chart_{ticker}",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "toImage"],
        },
    )
    st.caption("提示：框選可縮放 X 軸，平移或縮放後價格 Y 軸會依可視範圍自動調整。底部滑桿可查看更早歷史。點擊 ↩ 重置 或圖表右上角「Reset axes」可回到選定期間。")
    if indicator_flags["show_volume_profile"]:
        from src.ui.components.disclaimer_badge import render_disclaimer_badge
        render_disclaimer_badge("Volume Profile 含 Estimated Bar Delta，為估算值，僅供參考，非逐筆成交數據")


def _chart_indicator_flags(cfg: dict, chart_df: pd.DataFrame) -> dict[str, bool]:
    return {
        "show_macd": bool(cfg.get("show_macd", False)) and "histogram" in chart_df.columns,
        "show_kd": bool(cfg.get("show_kd", False)) and "K" in chart_df.columns,
        "show_bias": bool(cfg.get("show_bias", False)),
        "show_volume_bar": bool(cfg.get("show_volume_bar", False)),
        "show_volume_profile": bool(cfg.get("show_volume_profile", False)),
        "show_candlestick_patterns": bool(cfg.get("show_candlestick_patterns", False)),
        "show_ma_cross_labels": bool(cfg.get("show_ma_cross_labels", False)),
    }


def _render_ai_signal_explainer(
    ticker: str,
    user_id: str,
    df_full: pd.DataFrame,
    signal_layers: list[SignalLayer],
    today_buy: bool,
    today_sell: bool,
    *,
    result_in_expander: bool = True,
) -> None:
    key = f"ai_signal_explanation_{ticker}"
    cols = st.columns([1, 5])
    if cols[0].button("🤖 解讀", key=f"btn_ai_signal_{ticker}", help="用已設定的 AI provider 解讀目前訊號"):
        with st.spinner("產生 AI 解讀…"):
            try:
                chain = build_default_chain(user_id)
                st.session_state[key] = generate_signal_explanation(
                    chain,
                    ticker,
                    df_full,
                    signal_layers,
                    today_buy,
                    today_sell,
                )
            except MissingAIProviderConfig:
                st.session_state[key] = ""
                cols[1].info("尚未設定 AI API key，可至設定頁新增 Anthropic、Gemini 或 OpenAI key。")
            except AIProviderError as exc:
                st.session_state[key] = ""
                cols[1].error(f"AI 解讀失敗：{exc}")
            except Exception as exc:
                st.session_state[key] = ""
                cols[1].error(f"AI 解讀失敗：{exc}")

    if st.session_state.get(key) and result_in_expander:
        with st.expander("AI 訊號解讀", expanded=True):
            st.markdown(st.session_state[key])
    elif st.session_state.get(key):
        st.markdown(st.session_state[key])


def _get_ma_summary(df_full: pd.DataFrame) -> dict:
    try:
        return summarize_ma_state(df_full, DEFAULT_MA_PERIODS)
    except Exception:
        return {"score": 0, "stars": "—", "directions": {}, "month_above_quarter": False, "recent_crosses": []}


def _render_ma_analysis_panel(df_full: pd.DataFrame) -> None:
    st.divider()
    with st.expander("均線分析", expanded=True):
        _render_ma_analysis_content(df_full)


def _render_ma_analysis_content(df_full: pd.DataFrame) -> None:
    summary = summarize_ma_state(df_full, DEFAULT_MA_PERIODS)
    trend = detect_hh_hl(df_full.tail(180), pivot_window=5)
    necklines = detect_neckline(df_full, lookback=60)

    col_score, col_month, col_trend = st.columns([1, 1, 1])
    col_score.metric("多頭排列", summary["stars"], f"{summary['score']} / 4")
    col_month.metric("月線 > 季線", "是" if summary["month_above_quarter"] else "否")

    trend_help = (
        "多頭 (Uptrend)：最近兩個波段出現「高點過前高 (Higher High)」且「低點不破前低 (Higher Low)」\n\n"
        "空頭 (Downtrend)：最近兩個波段出現「高點不過前高 (Lower High)」且「低點破前低 (Lower Low)」\n\n"
        "盤整 (Sideways)：不符合上述兩者，屬於震盪洗盤格局"
    )
    col_trend.metric("趨勢", trend_label(trend["trend"]), help=trend_help)

    direction_cols = st.columns(6)
    arrow_map = {"上行": "↑", "下彎": "↓", "持平": "→"}
    for col, period in zip(direction_cols, DEFAULT_MA_PERIODS):
        direction = summary["directions"].get(period, "持平")
        col.markdown(f"**MA{period}**")
        col.caption(f"{arrow_map.get(direction, '→')} {direction}")

    hook = summary.get("hook_forecast_20", [])
    if hook:
        st.caption("未來日 MA20 扣抵")
        hook_df = pd.DataFrame({"未來日": [f"D+{i}" for i in range(1, len(hook) + 1)], "MA20扣抵": hook})
        chart = alt.Chart(hook_df).mark_line(point=True).encode(
            x=alt.X("未來日", sort=None, title=None),
            y=alt.Y("MA20扣抵", scale=alt.Scale(zero=False), title=None),
        ).properties(height=140)
        st.altair_chart(chart, width="stretch")

    recent_crosses = summary.get("recent_crosses", [])
    if recent_crosses:
        st.caption("近期 MA 交叉")
        st.dataframe(pd.DataFrame(recent_crosses).tail(5), hide_index=True, width="stretch")

    if necklines:
        st.caption("近 60 日支撐/壓力參考：" + " / ".join(f"{level:.2f}" for level in necklines))


def _render_strategy_d_diagnosis(
    df_full: pd.DataFrame,
    df_s: pd.DataFrame | None,
    sd_params: dict,
    vp_ctx: dict | None,
) -> None:
    if vp_ctx:
        poc_dist = vp_ctx.get("poc_distance_pct")
        in_zone = vp_ctx.get("in_support_zone", False)
        if poc_dist is not None:
            sign = "+" if float(poc_dist) >= 0 else ""
            zone_label = "✓ 支撐帶內" if in_zone else "— 非支撐帶"
            st.caption(f"VP 情境 ▸ 距最近 POC：**{sign}{float(poc_dist):.2f}%**　|　{zone_label}")

    if df_s is None:
        st.warning("Strategy D 指標計算失敗，無法執行診斷。")
        return

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
            return

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
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            st.caption(c.get("summary", ""))


def _recent_ma_cross_events(df_full: pd.DataFrame) -> list[dict]:
    events = []
    for fast, slow in [(5, 10), (10, 20), (20, 60), (60, 120), (120, 240)]:
        events.extend(ma_cross_signal(df_full, fast, slow)[-2:])
    return sorted(events, key=lambda item: item["date"])[-5:]


def _chart_dataframe(
    ticker: str,
    period: str,
    granularity: str,
    daily_df: pd.DataFrame,
    ma_periods: list[int],
    sd_params: dict,
    cfg: dict,
) -> pd.DataFrame:
    if granularity == "1d":
        return daily_df
    chart_df = fetch_prices_by_interval(ticker, granularity, period=period)
    if chart_df.empty:
        return daily_df
    chart_df = add_ma(chart_df, periods=ma_periods)
    try:
        chart_df = add_macd(
            chart_df,
            fast=sd_params["macd_fast"],
            slow=sd_params["macd_slow"],
            signal=sd_params["macd_signal"],
        )
    except ValueError:
        pass
    try:
        chart_df = add_kd(
            chart_df,
            k=sd_params["kd_k"],
            d=sd_params["kd_d"],
            smooth_k=sd_params["kd_smooth_k"],
        )
    except ValueError:
        pass
    try:
        chart_df = add_bias(chart_df, period=cfg["bias_period"])
    except ValueError:
        pass
    return chart_df


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
