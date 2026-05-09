from __future__ import annotations

import streamlit as st

from src.repositories.preferences_repo import get_preferences, save_preferences
from src.ui.pages.settings.defaults import load_defaults


def render_strategy_defaults_section(user_id: str) -> None:
    st.markdown("### Strategy Defaults")
    st.caption("設定後，sidebar 與 Scanner / Today / Stock 會使用保存後的策略參數。")
    if message := st.session_state.pop("_strategy_defaults_saved_message", None):
        st.success(str(message))

    prefs = get_preferences(user_id)
    defaults = load_defaults()
    _render_strategy_d_defaults(user_id, prefs, defaults["strategy_d"])
    st.divider()
    _render_strategy_kd_defaults(user_id, prefs, defaults.get("strategy_kd", {}))


def _render_strategy_d_defaults(user_id: str, prefs: dict, sd: dict) -> None:
    st.markdown("#### Strategy D")
    if st.button("重置 Strategy D 參數", key="settings_reset_strategy_d", width="content"):
        prefs.update(_strategy_d_default_values(sd))
        save_preferences(user_id, prefs)
        st.session_state["_strategy_defaults_saved_message"] = "已重置 Strategy D 參數"
        st.rerun()

    enable_sell = st.checkbox(
        "啟用賣出訊號",
        value=bool(prefs.get("enable_sell_signal", sd.get("enable_sell_signal", True))),
        key="settings_enable_sell_signal",
    )
    col1, col2 = st.columns(2)
    with col1:
        buy_kd_window = st.slider("買進 KD 回看視窗", 1, 10, int(prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"]))), key="settings_buy_kd_window")
        buy_n_bars = st.slider("買進 MACD 收斂根數", 3, 10, int(prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"]))), key="settings_buy_n_bars")
        buy_max_viol = st.slider("買進 MACD 容忍違反根數", 0, 3, int(prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"]))), key="settings_buy_max_violations", help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        buy_recovery = st.slider("買進回彈比例", 0.3, 0.9, float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"]))), step=0.05, key="settings_buy_recovery")
        buy_kd_thresh = st.slider("買進 KD 閾值", 10, 35, int(prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"]))), key="settings_buy_kd_thresh")
        buy_lookback = st.slider("買進 MACD 峰谷回看根數", 10, 40, int(prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"]))), key="settings_buy_lookback_bars")
    with col2:
        sell_kd_window = st.slider("賣出 KD 回看視窗", 1, 10, int(prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"]))), disabled=not enable_sell, key="settings_sell_kd_window")
        sell_n_bars = st.slider("賣出 MACD 收斂根數", 3, 10, int(prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"]))), disabled=not enable_sell, key="settings_sell_n_bars")
        sell_max_viol = st.slider("賣出 MACD 容忍違反根數", 0, 3, int(prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"]))), disabled=not enable_sell, key="settings_sell_max_violations", help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        sell_recovery = st.slider("賣出回落比例", 0.3, 0.9, float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"]))), step=0.05, disabled=not enable_sell, key="settings_sell_recovery")
        sell_kd_thresh = st.slider("賣出 KD 閾值", 65, 95, int(prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"]))), disabled=not enable_sell, key="settings_sell_kd_thresh")
        sell_lookback = st.slider("賣出 MACD 峰谷回看根數", 10, 40, int(prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"]))), disabled=not enable_sell, key="settings_sell_lookback_bars")

    if st.button("儲存 Strategy D 參數", key="settings_save_strategy_d"):
        prefs.update({
            "enable_sell_signal": bool(enable_sell),
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
        st.session_state["_strategy_defaults_saved_message"] = "已儲存 Strategy D 參數"
        st.rerun()


def _render_strategy_kd_defaults(user_id: str, prefs: dict, skd: dict) -> None:
    st.markdown("#### Strategy KD")
    if st.button("重置 Strategy KD 參數", key="settings_reset_strategy_kd", width="content"):
        prefs.update(_strategy_kd_default_values(skd))
        save_preferences(user_id, prefs)
        st.session_state["_strategy_defaults_saved_message"] = "已重置 Strategy KD 參數"
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        enable_k_thresh = st.checkbox("啟用低檔篩選（黃金交叉）", value=bool(prefs.get("skd_enable_k_thresh", False)), help="僅在 K 值低於閾值時才計算黃金交叉", key="settings_skd_enable_k_thresh")
        skd_k_thresh = st.slider("黃金交叉 K 閾值", 10, 50, int(prefs.get("skd_k_threshold", skd.get("k_threshold") or 30)), disabled=not enable_k_thresh, key="settings_skd_k_thresh")
    with col2:
        enable_d_thresh = st.checkbox("啟用高檔篩選（死亡交叉）", value=bool(prefs.get("skd_enable_d_thresh", False)), help="僅在 K 值高於閾值時才計算死亡交叉", key="settings_skd_enable_d_thresh")
        skd_d_thresh = st.slider("死亡交叉 K 閾值", 50, 90, int(prefs.get("skd_d_threshold", skd.get("d_threshold") or 70)), disabled=not enable_d_thresh, key="settings_skd_d_thresh")
    skd_enable_sell = st.checkbox("啟用賣出訊號", value=bool(prefs.get("skd_enable_sell", skd.get("enable_sell", True))), key="settings_skd_enable_sell")

    if st.button("儲存 Strategy KD 參數", key="settings_save_strategy_kd"):
        prefs.update({
            "skd_enable_k_thresh": bool(enable_k_thresh),
            "skd_k_threshold": skd_k_thresh,
            "skd_enable_d_thresh": bool(enable_d_thresh),
            "skd_d_threshold": skd_d_thresh,
            "skd_enable_sell": bool(skd_enable_sell),
        })
        save_preferences(user_id, prefs)
        st.session_state["_strategy_defaults_saved_message"] = "已儲存 Strategy KD 參數"
        st.rerun()


def _strategy_d_default_values(sd: dict) -> dict:
    return {
        "buy_kd_window": sd["buy_kd_window"],
        "buy_n_bars": sd["buy_n_bars"],
        "buy_recovery_pct": sd["buy_recovery_pct"],
        "buy_kd_k_threshold": sd["buy_kd_k_threshold"],
        "buy_max_violations": sd["buy_max_violations"],
        "buy_lookback_bars": sd["buy_lookback_bars"],
        "sell_kd_window": sd["sell_kd_window"],
        "sell_n_bars": sd["sell_n_bars"],
        "sell_recovery_pct": sd["sell_recovery_pct"],
        "sell_kd_d_threshold": sd["sell_kd_d_threshold"],
        "sell_max_violations": sd["sell_max_violations"],
        "sell_lookback_bars": sd["sell_lookback_bars"],
        "enable_sell_signal": sd.get("enable_sell_signal", True),
    }


def _strategy_kd_default_values(skd: dict) -> dict:
    return {
        "skd_enable_k_thresh": False,
        "skd_k_threshold": skd.get("k_threshold") or 30,
        "skd_enable_d_thresh": False,
        "skd_d_threshold": skd.get("d_threshold") or 70,
        "skd_enable_sell": skd.get("enable_sell", True),
    }
