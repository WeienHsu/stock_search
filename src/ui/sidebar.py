import json
from pathlib import Path

import streamlit as st

import src.strategies.strategy_d    # ensure registration
import src.strategies.strategy_kd   # ensure registration

_SETTINGS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"

_THEME_OPTIONS = {"Morandi 暖色": "morandi", "Dark 深色": "dark"}
_THEME_LABELS  = {v: k for k, v in _THEME_OPTIONS.items()}

_STRATEGY_LABELS = {
    "strategy_d":  "Strategy D（MACD + KD）",
    "strategy_kd": "Strategy KD（黃金 / 死亡交叉）",
}


def _load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render_sidebar(user_id: str) -> dict:
    """Render sidebar and return a config dict with all user selections."""
    from src.repositories.preferences_repo import get_preferences, save_preferences
    from src.core.strategy_registry import list_strategies
    from src.repositories.watchlist_repo import get_watchlist
    from src.ui.components.sidebar_search import build_search_candidates, format_candidate, fuzzy_ticker_matches

    defaults = _load_defaults()
    prefs = get_preferences(user_id)

    st.sidebar.title("Stock Intelligence")

    # ── Theme selector ──
    saved_theme = prefs.get("theme", "morandi")
    current_label = _THEME_LABELS.get(saved_theme, "Morandi 暖色")
    selected_label = st.sidebar.selectbox(
        "色系",
        options=list(_THEME_OPTIONS.keys()),
        index=list(_THEME_OPTIONS.keys()).index(current_label),
    )
    selected_theme = _THEME_OPTIONS[selected_label]

    # Apply theme to session_state; rerun once if theme changed so CSS refreshes
    if st.session_state.get("theme") != selected_theme:
        st.session_state["theme"] = selected_theme
        prefs["theme"] = selected_theme
        save_preferences(user_id, prefs)
        st.rerun()

    st.sidebar.markdown("---")

    # ── Ticker input ──
    st.sidebar.markdown("**快速搜尋**")
    candidates = build_search_candidates(get_watchlist(user_id), defaults.get("watchlist_defaults", []))
    search_query = st.sidebar.text_input(
        "搜尋股票",
        placeholder="輸入代號或名稱",
        key="sidebar_quick_search",
        label_visibility="collapsed",
    )
    matches = fuzzy_ticker_matches(search_query, candidates)
    if matches:
        selected_candidate = st.sidebar.selectbox(
            "搜尋結果",
            matches,
            format_func=format_candidate,
            key="sidebar_quick_search_result",
            label_visibility="collapsed",
        )
        if st.sidebar.button("開啟 Dashboard", use_container_width=True, key="btn_open_dashboard_search"):
            st.session_state["_pending_nav_page"] = "📊 Dashboard"
            st.session_state["_pending_ticker"] = selected_candidate["ticker"]
            st.rerun()
    elif search_query.strip():
        st.sidebar.caption("找不到符合的自選股")

    nav_ticker = normalize_query_ticker()
    if nav_ticker and nav_ticker != st.session_state.get("_applied_query_ticker"):
        st.session_state["sidebar_ticker"] = nav_ticker
        st.session_state["_applied_query_ticker"] = nav_ticker
    ticker = st.sidebar.text_input(
        "股票代號", value=nav_ticker or prefs.get("last_ticker", defaults["ui"]["default_ticker"]),
        placeholder="e.g. 2330.TW / TSLA",
        key="sidebar_ticker",
    ).strip().upper()
    if st.sidebar.button("開啟綜合看盤", use_container_width=True):
        st.session_state["_pending_nav_page"] = "🖥️ 綜合看盤"
        st.session_state["_pending_ticker"] = ticker
        st.rerun()

    # ── Time period ──
    _avail_periods = defaults["ui"]["available_periods"]
    _saved_period = prefs.get("default_period", "6M")
    _period_idx = _avail_periods.index(_saved_period) if _saved_period in _avail_periods else _avail_periods.index("6M")
    period = st.sidebar.radio(
        "快速縮放",
        options=_avail_periods,
        index=_period_idx,
        horizontal=True,
    )

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
    kline_granularity = st.sidebar.selectbox(
        "K線週期",
        options=list(granularity_options.keys()),
        index=list(granularity_options.keys()).index(prefs.get("kline_granularity", "1d"))
        if prefs.get("kline_granularity", "1d") in granularity_options
        else 5,
        format_func=lambda value: granularity_options[value],
    )

    st.sidebar.markdown("---")

    # ── Active strategies (Dashboard chart overlay) ──
    all_strategies = list_strategies()
    saved_active = [s for s in prefs.get("active_strategies", ["strategy_d"]) if s in all_strategies]
    if not saved_active:
        saved_active = ["strategy_d"]
    active_strategies = st.sidebar.multiselect(
        "顯示策略訊號",
        options=all_strategies,
        default=saved_active,
        format_func=lambda x: _STRATEGY_LABELS.get(x, x),
    )

    st.sidebar.markdown("---")

    # ── Strategy D params (collapsible) ──
    sd = defaults["strategy_d"]
    with st.sidebar.expander("Strategy D 參數", expanded=False):
        st.caption("買進與賣出可分開調整；未保存的新使用者會沿用既有預設值。")
        buy_kd_window = st.slider("買進 KD 回看視窗", 1, 10, prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"])))
        buy_n_bars = st.slider("買進 MACD 收斂根數", 3, 10, prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"])))
        buy_max_viol = st.slider(
            "買進 MACD 容忍違反根數", 0, 3,
            prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"])),
            help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）",
        )
        buy_lookback = st.slider("買進 MACD 峰谷回看根數", 10, 40, prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"])))
        buy_recovery = st.slider(
            "買進回彈比例 (%)", 0.3, 0.9,
            float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"]))), step=0.05,
        )
        buy_kd_thresh = st.slider(
            "買進 KD 閾值（低檔）", 10, 35,
            prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"])),
        )
        enable_sell = st.checkbox("啟用賣出訊號", value=prefs.get("enable_sell_signal", sd.get("enable_sell_signal", True)), key="sd_enable_sell")
        sell_kd_window = st.slider("賣出 KD 回看視窗", 1, 10, prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"])), disabled=not enable_sell)
        sell_n_bars = st.slider("賣出 MACD 收斂根數", 3, 10, prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"])), disabled=not enable_sell)
        sell_max_viol = st.slider(
            "賣出 MACD 容忍違反根數", 0, 3,
            prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"])),
            disabled=not enable_sell,
            help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）",
        )
        sell_lookback = st.slider("賣出 MACD 峰谷回看根數", 10, 40, prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"])), disabled=not enable_sell)
        sell_recovery = st.slider(
            "賣出回落比例 (%)", 0.3, 0.9,
            float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"]))), step=0.05,
            disabled=not enable_sell,
        )
        sell_kd_d_thresh = st.slider(
            "賣出 KD 閾值（高檔）", 65, 95,
            prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"])),
            disabled=not enable_sell,
        )

    # ── Strategy KD params (collapsible) ──
    skd = defaults.get("strategy_kd", {})
    with st.sidebar.expander("Strategy KD 參數", expanded=False):
        enable_k_thresh = st.checkbox(
            "啟用低檔篩選（黃金交叉）",
            value=prefs.get("skd_enable_k_thresh", False),
            help="僅在 K 值低於閾值時才計算黃金交叉",
            key="skd_enable_k_thresh",
        )
        skd_k_thresh = st.slider(
            "黃金交叉 K 閾值", 10, 50,
            prefs.get("skd_k_threshold", 30),
            disabled=not enable_k_thresh,
            key="skd_k_thresh_slider",
        )
        enable_d_thresh = st.checkbox(
            "啟用高檔篩選（死亡交叉）",
            value=prefs.get("skd_enable_d_thresh", False),
            help="僅在 K 值高於閾值時才計算死亡交叉",
            key="skd_enable_d_thresh",
        )
        skd_d_thresh = st.slider(
            "死亡交叉 K 閾值", 50, 90,
            prefs.get("skd_d_threshold", 70),
            disabled=not enable_d_thresh,
            key="skd_d_thresh_slider",
        )
        skd_enable_sell = st.checkbox(
            "啟用賣出訊號",
            value=prefs.get("skd_enable_sell", skd.get("enable_sell", True)),
            key="skd_enable_sell",
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**指標顯示**")

    show_macd = st.sidebar.checkbox("MACD", value=prefs.get("show_macd", True))
    show_kd   = st.sidebar.checkbox("KD",   value=prefs.get("show_kd",   True))
    show_bias = st.sidebar.checkbox("乖離率", value=prefs.get("show_bias", True))
    show_news = st.sidebar.checkbox("新聞情緒", value=prefs.get("show_news", True))
    show_candlestick_patterns = st.sidebar.checkbox("K線形態", value=prefs.get("show_candlestick_patterns", True))
    show_volume_profile = st.sidebar.checkbox("Volume Profile", value=prefs.get("show_volume_profile", False))
    show_ma_cross_labels = st.sidebar.checkbox("MA交叉標註", value=prefs.get("show_ma_cross_labels", True))

    bias_period = st.sidebar.slider(
        "乖離率週期",
        min_value=int(defaults["bias"]["min_period"]),
        max_value=int(defaults["bias"]["max_period"]),
        value=int(prefs.get("bias_period", defaults["bias"]["period"])),
        step=1,
    ) if show_bias else defaults["bias"]["period"]

    st.sidebar.markdown("---")
    st.sidebar.markdown("**MA 均線**")
    ma_periods = st.sidebar.multiselect(
        "顯示均線",
        options=[5, 10, 20, 60, 120, 240],
        default=prefs.get("ma_periods", [5, 20, 60]),
    )

    # Shared KD indicator params (reused by both strategies)
    kd_indicator = {k: sd[k] for k in ("kd_k", "kd_d", "kd_smooth_k")}

    return {
        "ticker": ticker,
        "period": period,
        "kline_granularity": kline_granularity,
        "active_strategies": active_strategies,
        "strategy_d": {
            "kd_window": buy_kd_window,
            "n_bars": buy_n_bars,
            "recovery_pct": buy_recovery,
            "kd_k_threshold": buy_kd_thresh,
            "kd_d_threshold": sell_kd_d_thresh,
            "max_violations": buy_max_viol,
            "lookback_bars": buy_lookback,
            "enable_sell_signal": enable_sell,
            "buy_kd_window": buy_kd_window,
            "buy_n_bars": buy_n_bars,
            "buy_recovery_pct": buy_recovery,
            "buy_kd_k_threshold": buy_kd_thresh,
            "buy_max_violations": buy_max_viol,
            "buy_lookback_bars": buy_lookback,
            "sell_kd_window": sell_kd_window,
            "sell_n_bars": sell_n_bars,
            "sell_recovery_pct": sell_recovery,
            "sell_kd_d_threshold": sell_kd_d_thresh,
            "sell_max_violations": sell_max_viol,
            "sell_lookback_bars": sell_lookback,
            **{k: sd[k] for k in ("macd_fast", "macd_slow", "macd_signal", "kd_k", "kd_d", "kd_smooth_k")},
        },
        "strategy_kd": {
            "k_threshold": skd_k_thresh if enable_k_thresh else None,
            "d_threshold": skd_d_thresh if enable_d_thresh else None,
            "enable_sell": skd_enable_sell,
            **kd_indicator,
        },
        "show_macd": show_macd,
        "show_kd": show_kd,
        "show_bias": show_bias,
        "show_news": show_news,
        "show_candlestick_patterns": show_candlestick_patterns,
        "show_volume_profile": show_volume_profile,
        "show_ma_cross_labels": show_ma_cross_labels,
        "bias_period": int(bias_period),
        "ma_periods": ma_periods,
    }


def normalize_query_ticker() -> str:
    try:
        ticker = st.query_params.get("ticker", "")
        if isinstance(ticker, list):
            ticker = ticker[0] if ticker else ""
        return str(ticker).strip().upper()
    except Exception:
        return ""
