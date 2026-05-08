from __future__ import annotations

import streamlit as st

from src.repositories.preferences_repo import get_preferences, save_preferences
from src.ui.pages.settings.defaults import load_defaults


def render_preferences_section(user_id: str) -> None:
    st.markdown("### 偏好設定")
    prefs = get_preferences(user_id)
    defaults = load_defaults()

    periods = defaults["ui"]["available_periods"]
    saved_default = prefs.get("default_period", "6M")
    default_idx = periods.index(saved_default) if saved_default in periods else periods.index("6M")
    default_period = st.selectbox("預設快速縮放", periods, index=default_idx)

    st.markdown("#### 圖表預設顯示")
    col1, col2 = st.columns(2)
    with col1:
        show_macd = st.checkbox("MACD", value=bool(prefs.get("show_macd", True)), key="settings_show_macd")
        show_kd = st.checkbox("KD", value=bool(prefs.get("show_kd", True)), key="settings_show_kd")
        show_bias = st.checkbox("乖離率", value=bool(prefs.get("show_bias", True)), key="settings_show_bias")
        show_news = st.checkbox("新聞情緒", value=bool(prefs.get("show_news", True)), key="settings_show_news")
    with col2:
        show_volume_bar = st.checkbox("日成交量", value=bool(prefs.get("show_volume_bar", True)), key="settings_show_volume_bar")
        show_volume_profile = st.checkbox("Volume Profile", value=bool(prefs.get("show_volume_profile", True)), key="settings_show_volume_profile")
        show_candlestick_patterns = st.checkbox("K線形態", value=bool(prefs.get("show_candlestick_patterns", False)), key="settings_show_candlestick")
        show_ma_cross_labels = st.checkbox("MA交叉標註", value=bool(prefs.get("show_ma_cross_labels", False)), key="settings_show_ma_cross")

    bias_defaults = defaults["bias"]
    bias_period = st.slider(
        "乖離率週期",
        min_value=int(bias_defaults["min_period"]),
        max_value=int(bias_defaults["max_period"]),
        value=int(prefs.get("bias_period", bias_defaults["period"])),
        step=1,
        key="settings_bias_period",
    )

    if st.button("儲存偏好"):
        prefs.update({
            "default_period": default_period,
            "show_macd": show_macd,
            "show_kd": show_kd,
            "show_bias": show_bias,
            "show_news": show_news,
            "show_volume_bar": show_volume_bar,
            "show_volume_profile": show_volume_profile,
            "show_candlestick_patterns": show_candlestick_patterns,
            "show_ma_cross_labels": show_ma_cross_labels,
            "bias_period": int(bias_period),
        })
        save_preferences(user_id, prefs)
        st.success("已儲存")
