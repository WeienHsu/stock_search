import json
from pathlib import Path

import streamlit as st

_SETTINGS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"

_THEME_OPTIONS = {"Morandi 暖色": "morandi", "Dark 深色": "dark"}
_THEME_LABELS  = {v: k for k, v in _THEME_OPTIONS.items()}


def _load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render_sidebar(user_id: str) -> dict:
    """Render sidebar and return a config dict with all user selections."""
    from src.repositories.preferences_repo import get_preferences, save_preferences

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
    ticker = st.sidebar.text_input(
        "股票代號", value=prefs.get("last_ticker", defaults["ui"]["default_ticker"]),
        placeholder="e.g. 2330.TW / TSLA",
    ).strip().upper()

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

    st.sidebar.markdown("---")

    # ── Strategy D params (collapsible) ──
    sd = defaults["strategy_d"]
    with st.sidebar.expander("Strategy D 參數", expanded=False):
        kd_window  = st.slider("KD 回看視窗", 5, 20, prefs.get("kd_window", sd["kd_window"]))
        n_bars     = st.slider("MACD 收斂根數", 3, 10, prefs.get("n_bars", sd["n_bars"]))
        max_viol   = st.slider("MACD 容忍違反根數", 0, 3, prefs.get("max_violations", sd.get("max_violations", 1)),
                               help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        lookback   = st.slider("MACD 峰谷回看根數", 10, 40, prefs.get("lookback_bars", sd.get("lookback_bars", 20)))
        recovery   = st.slider("回彈比例 (%)", 0.3, 0.9,
                               float(prefs.get("recovery_pct", sd["recovery_pct"])), step=0.05)
        kd_thresh  = st.slider("買進 KD 閾值（低檔）", 10, 35,
                               prefs.get("kd_k_threshold", sd["kd_k_threshold"]))
        enable_sell = st.checkbox("啟用賣出訊號", value=prefs.get("enable_sell_signal", sd.get("enable_sell_signal", True)))
        kd_d_thresh = st.slider("賣出 KD 閾值（高檔）", 65, 95,
                                prefs.get("kd_d_threshold", sd.get("kd_d_threshold", 80)),
                                disabled=not enable_sell)

    st.sidebar.markdown("---")

    # ── Y-axis auto-scale ──
    auto_y_scale = st.sidebar.checkbox(
        "Y 軸跟隨可視範圍",
        value=prefs.get("auto_y_scale", True),
        help="勾選：圖表依選定期間裁切，Y 軸自動貼合價格範圍。\n取消：顯示完整 5 年資料 + 底部時間滑桿，Y 軸保持全範圍刻度。",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**指標顯示**")

    show_macd = st.sidebar.checkbox("MACD", value=prefs.get("show_macd", True))
    show_kd   = st.sidebar.checkbox("KD",   value=prefs.get("show_kd",   True))
    show_bias = st.sidebar.checkbox("乖離率", value=prefs.get("show_bias", True))
    show_news = st.sidebar.checkbox("新聞情緒", value=prefs.get("show_news", True))

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
        options=[5, 10, 20, 60, 120],
        default=prefs.get("ma_periods", [5, 20, 60]),
    )

    return {
        "ticker": ticker,
        "period": period,
        "auto_y_scale": auto_y_scale,
        "strategy_d": {
            "kd_window": kd_window,
            "n_bars": n_bars,
            "recovery_pct": recovery,
            "kd_k_threshold": kd_thresh,
            "kd_d_threshold": kd_d_thresh,
            "max_violations": max_viol,
            "lookback_bars": lookback,
            "enable_sell_signal": enable_sell,
            **{k: sd[k] for k in ("macd_fast", "macd_slow", "macd_signal", "kd_k", "kd_d", "kd_smooth_k")},
        },
        "show_macd": show_macd,
        "show_kd": show_kd,
        "show_bias": show_bias,
        "show_news": show_news,
        "bias_period": int(bias_period),
        "ma_periods": ma_periods,
    }
