import json
from pathlib import Path

import streamlit as st

_SETTINGS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"


def _load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render_sidebar(user_id: str) -> dict:
    """
    Render sidebar controls and return a config dict with all user selections.
    Reads saved preferences on load; sidebar changes are in-session only.
    """
    from src.repositories.preferences_repo import get_preferences

    defaults = _load_defaults()
    prefs = get_preferences(user_id)

    st.sidebar.title("Stock Intelligence")
    st.sidebar.markdown("---")

    # ── Ticker input ──
    ticker = st.sidebar.text_input(
        "股票代號", value=prefs.get("last_ticker", defaults["ui"]["default_ticker"]),
        placeholder="e.g. 2330.TW / TSLA",
    ).strip().upper()

    # ── Time period ──
    period = st.sidebar.radio(
        "時間區間",
        options=defaults["ui"]["available_periods"],
        index=defaults["ui"]["available_periods"].index(prefs.get("default_period", "6M")),
        horizontal=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Strategy D 參數**")

    sd = defaults["strategy_d"]
    kd_window = st.sidebar.slider("KD 回看視窗", 5, 20, prefs.get("kd_window", sd["kd_window"]))
    n_bars     = st.sidebar.slider("MACD 收斂根數", 2, 7,  prefs.get("n_bars",    sd["n_bars"]))
    recovery   = st.sidebar.slider("回彈比例 (%)",  0.3, 0.9, float(prefs.get("recovery_pct", sd["recovery_pct"])), step=0.05)
    kd_thresh  = st.sidebar.slider("KD 閾值",       10, 35,  prefs.get("kd_k_threshold", sd["kd_k_threshold"]))

    st.sidebar.markdown("---")
    st.sidebar.markdown("**指標顯示**")

    show_macd = st.sidebar.checkbox("MACD", value=prefs.get("show_macd", True))
    show_kd   = st.sidebar.checkbox("KD",   value=prefs.get("show_kd",   True))
    show_bias = st.sidebar.checkbox("乖離率", value=prefs.get("show_bias", True))
    show_news = st.sidebar.checkbox("新聞情緒", value=prefs.get("show_news", True))

    bias_period = st.sidebar.select_slider(
        "乖離率週期",
        options=defaults["bias"]["available_periods"],
        value=prefs.get("bias_period", defaults["bias"]["period"]),
    ) if show_bias else defaults["bias"]["period"]

    st.sidebar.markdown("---")
    st.sidebar.markdown("**MA 均線**")
    ma_periods = st.sidebar.multiselect(
        "顯示均線",
        options=[5, 10, 20, 60],
        default=prefs.get("ma_periods", [5, 20, 60]),
    )

    return {
        "ticker": ticker,
        "period": period,
        "strategy_d": {
            "kd_window": kd_window,
            "n_bars": n_bars,
            "recovery_pct": recovery,
            "kd_k_threshold": kd_thresh,
            **{k: sd[k] for k in ("macd_fast", "macd_slow", "macd_signal", "kd_k", "kd_d", "kd_smooth_k")},
        },
        "show_macd": show_macd,
        "show_kd": show_kd,
        "show_bias": show_bias,
        "show_news": show_news,
        "bias_period": int(bias_period),
        "ma_periods": ma_periods,
    }
