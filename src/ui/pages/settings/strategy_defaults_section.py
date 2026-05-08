from __future__ import annotations

import streamlit as st

from src.repositories.preferences_repo import get_preferences, save_preferences
from src.ui.pages.settings.defaults import load_defaults


def render_strategy_defaults_section(user_id: str) -> None:
    st.markdown("### Strategy D 參數預設值")
    st.caption("設定後，側邊欄的參數滑桿將以此作為預設值。")

    prefs = get_preferences(user_id)
    sd = load_defaults()["strategy_d"]

    col1, col2 = st.columns(2)
    with col1:
        buy_kd_window = st.slider("買進 KD 回看視窗", 1, 10, int(prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"]))), key="settings_buy_kd_window")
        buy_n_bars = st.slider("買進 MACD 收斂根數", 3, 10, int(prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"]))), key="settings_buy_n_bars")
        buy_max_viol = st.slider("買進 MACD 容忍違反根數", 0, 3, int(prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"]))), key="settings_buy_max_violations", help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        buy_recovery = st.slider("買進回彈比例", 0.3, 0.9, float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"]))), step=0.05, key="settings_buy_recovery")
        buy_kd_thresh = st.slider("買進 KD 閾值", 10, 35, int(prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"]))), key="settings_buy_kd_thresh")
        buy_lookback = st.slider("買進 MACD 峰谷回看根數", 10, 40, int(prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"]))), key="settings_buy_lookback_bars")
    with col2:
        sell_kd_window = st.slider("賣出 KD 回看視窗", 1, 10, int(prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"]))), key="settings_sell_kd_window")
        sell_n_bars = st.slider("賣出 MACD 收斂根數", 3, 10, int(prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"]))), key="settings_sell_n_bars")
        sell_max_viol = st.slider("賣出 MACD 容忍違反根數", 0, 3, int(prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"]))), key="settings_sell_max_violations", help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        sell_recovery = st.slider("賣出回落比例", 0.3, 0.9, float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"]))), step=0.05, key="settings_sell_recovery")
        sell_kd_thresh = st.slider("賣出 KD 閾值", 65, 95, int(prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"]))), key="settings_sell_kd_thresh")
        sell_lookback = st.slider("賣出 MACD 峰谷回看根數", 10, 40, int(prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"]))), key="settings_sell_lookback_bars")

    if st.button("儲存 Strategy D 參數"):
        prefs.update({
            "buy_kd_window": buy_kd_window,
            "buy_n_bars": buy_n_bars,
            "buy_recovery_pct": buy_recovery,
            "buy_kd_k_threshold": buy_kd_thresh,
            "buy_max_violations": buy_max_viol,
            "buy_lookback_bars": buy_lookback,
            "sell_kd_window": sell_kd_window,
            "sell_n_bars": sell_n_bars,
            "sell_recovery_pct": sell_recovery,
            "sell_kd_d_threshold": sell_kd_thresh,
            "sell_max_violations": sell_max_viol,
            "sell_lookback_bars": sell_lookback,
        })
        save_preferences(user_id, prefs)
        st.success("已儲存 Strategy D 參數，側邊欄下次展開時將使用新預設值")
