import json
from pathlib import Path

import streamlit as st

import src.strategies.strategy_d    # ensure registration
import src.strategies.strategy_kd   # ensure registration
from src.ui.components.sidebar_strategy_params import render_strategy_param_controls
from src.ui.nav.page_keys import DASHBOARD, LABEL_BY_KEY, WORKSTATION

_SETTINGS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"

_THEME_OPTIONS = {"Morandi 暖色": "morandi", "Dark 深色": "dark", "跟隨系統": "system"}
_THEME_LABELS  = {v: k for k, v in _THEME_OPTIONS.items()}

_STRATEGY_LABELS = {
    "strategy_d":  "Strategy D 訊號",
    "strategy_kd": "Strategy KD 訊號",
}


def _load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize_saved_active_strategies(
    all_strategies: list[str],
    saved_active: list[str] | None,
    default_strategy: str = "strategy_d",
) -> list[str]:
    if saved_active is None:
        return [default_strategy] if default_strategy in all_strategies else []

    if not saved_active:
        return []

    active = [strategy_id for strategy_id in saved_active if strategy_id in all_strategies]
    if active:
        return active
    return [default_strategy] if default_strategy in all_strategies else []


def _active_strategies_from_toggles(strategy_toggles: dict[str, bool]) -> list[str]:
    return [strategy_id for strategy_id, checked in strategy_toggles.items() if checked]


def _strategy_param_expander_label(strategy_id: str, title: str, active_strategies: list[str]) -> str:
    marker = "✅" if strategy_id in active_strategies else "⬜"
    return f"{marker} {title}"


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
    selected_label = st.sidebar.segmented_control(
        "色系",
        options=list(_THEME_OPTIONS.keys()),
        default=current_label,
        key="sidebar_theme_selector",
    )
    selected_theme = _THEME_OPTIONS[selected_label or current_label]

    # Apply theme to session_state; rerun once if theme changed so CSS refreshes
    if st.session_state.get("theme") != selected_theme:
        st.session_state["theme"] = selected_theme
        prefs["theme"] = selected_theme
        save_preferences(user_id, prefs)
        st.rerun()

    st.sidebar.divider()

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
            st.session_state["_pending_nav_page"] = LABEL_BY_KEY[DASHBOARD]
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
        st.session_state["_pending_nav_page"] = LABEL_BY_KEY[WORKSTATION]
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

    st.sidebar.divider()

    # ── Strategy overlays ──
    all_strategies = list_strategies()
    saved_active = _normalize_saved_active_strategies(all_strategies, prefs.get("active_strategies"))

    st.sidebar.markdown("**策略訊號**")
    strategy_toggles = {}
    for strategy_id in all_strategies:
        label = _STRATEGY_LABELS.get(strategy_id, strategy_id)
        strategy_toggles[strategy_id] = st.sidebar.checkbox(
            label,
            value=strategy_id in saved_active,
            key=f"show_{strategy_id}",
        )
    active_strategies = _active_strategies_from_toggles(strategy_toggles)
    if active_strategies != prefs.get("active_strategies"):
        prefs["active_strategies"] = active_strategies
        save_preferences(user_id, prefs)

    show_macd = bool(prefs.get("show_macd", True))
    show_kd = bool(prefs.get("show_kd", True))
    show_bias = bool(prefs.get("show_bias", True))
    show_news = bool(prefs.get("show_news", True))
    show_volume_bar = bool(prefs.get("show_volume_bar", True))
    show_volume_profile = bool(prefs.get("show_volume_profile", True))
    show_candlestick_patterns = bool(prefs.get("show_candlestick_patterns", False))
    show_ma_cross_labels = bool(prefs.get("show_ma_cross_labels", False))
    bias_period = int(prefs.get("bias_period", defaults["bias"]["period"]))

    st.sidebar.divider()

    strategy_d_params, strategy_kd_params = render_strategy_param_controls(
        user_id,
        defaults,
        prefs,
        active_strategies,
    )

    st.sidebar.divider()
    st.sidebar.markdown("**MA 均線**")
    ma_periods = st.sidebar.multiselect(
        "顯示均線",
        options=[5, 10, 20, 60, 120, 240],
        default=prefs.get("ma_periods", [5, 20, 60]),
    )

    return {
        "ticker": ticker,
        "period": period,
        "kline_granularity": kline_granularity,
        "active_strategies": active_strategies,
        "strategy_d": strategy_d_params,
        "strategy_kd": strategy_kd_params,
        "show_macd": show_macd,
        "show_kd": show_kd,
        "show_bias": show_bias,
        "show_news": show_news,
        "show_volume_bar": show_volume_bar,
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
