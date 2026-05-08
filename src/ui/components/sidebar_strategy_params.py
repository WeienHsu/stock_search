from __future__ import annotations

import streamlit as st

from src.repositories.preferences_repo import save_preferences


def render_strategy_param_controls(
    user_id: str,
    defaults: dict,
    prefs: dict,
    active_strategies: list[str],
) -> tuple[dict, dict]:
    sd = defaults["strategy_d"]
    with st.sidebar.expander(_strategy_param_expander_label("strategy_d", "Strategy D 參數", active_strategies), expanded=False):
        st.caption("買進與賣出可分開調整；未保存的新使用者會沿用既有預設值。")
        if st.button("重置 Strategy D 參數", key="reset_strategy_d_params", use_container_width=True):
            _reset_strategy_d(user_id, prefs, sd)
        buy_kd_window = st.slider("買進 KD 回看視窗", 1, 10, prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"])))
        buy_n_bars = st.slider("買進 MACD 收斂根數", 3, 10, prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"])))
        buy_max_viol = st.slider("買進 MACD 容忍違反根數", 0, 3, prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"])), help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        buy_lookback = st.slider("買進 MACD 峰谷回看根數", 10, 40, prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"])))
        buy_recovery = st.slider("買進回彈比例 (%)", 0.3, 0.9, float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"]))), step=0.05)
        buy_kd_thresh = st.slider("買進 KD 閾值（低檔）", 10, 35, prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"])))
        enable_sell = st.checkbox("啟用賣出訊號", value=prefs.get("enable_sell_signal", sd.get("enable_sell_signal", True)), key="sd_enable_sell")
        sell_kd_window = st.slider("賣出 KD 回看視窗", 1, 10, prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"])), disabled=not enable_sell)
        sell_n_bars = st.slider("賣出 MACD 收斂根數", 3, 10, prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"])), disabled=not enable_sell)
        sell_max_viol = st.slider("賣出 MACD 容忍違反根數", 0, 3, prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"])), disabled=not enable_sell, help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）")
        sell_lookback = st.slider("賣出 MACD 峰谷回看根數", 10, 40, prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"])), disabled=not enable_sell)
        sell_recovery = st.slider("賣出回落比例 (%)", 0.3, 0.9, float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"]))), step=0.05, disabled=not enable_sell)
        sell_kd_d_thresh = st.slider("賣出 KD 閾值（高檔）", 65, 95, prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"])), disabled=not enable_sell)

    skd = defaults.get("strategy_kd", {})
    with st.sidebar.expander(_strategy_param_expander_label("strategy_kd", "Strategy KD 參數", active_strategies), expanded=False):
        if st.button("重置 Strategy KD 參數", key="reset_strategy_kd_params", use_container_width=True):
            _reset_strategy_kd(user_id, prefs, skd)
        enable_k_thresh = st.checkbox("啟用低檔篩選（黃金交叉）", value=prefs.get("skd_enable_k_thresh", False), help="僅在 K 值低於閾值時才計算黃金交叉", key="skd_enable_k_thresh")
        skd_k_thresh = st.slider("黃金交叉 K 閾值", 10, 50, prefs.get("skd_k_threshold", 30), disabled=not enable_k_thresh, key="skd_k_thresh_slider")
        enable_d_thresh = st.checkbox("啟用高檔篩選（死亡交叉）", value=prefs.get("skd_enable_d_thresh", False), help="僅在 K 值高於閾值時才計算死亡交叉", key="skd_enable_d_thresh")
        skd_d_thresh = st.slider("死亡交叉 K 閾值", 50, 90, prefs.get("skd_d_threshold", 70), disabled=not enable_d_thresh, key="skd_d_thresh_slider")
        skd_enable_sell = st.checkbox("啟用賣出訊號", value=prefs.get("skd_enable_sell", skd.get("enable_sell", True)), key="skd_enable_sell")

    kd_indicator = {k: sd[k] for k in ("kd_k", "kd_d", "kd_smooth_k")}
    return (
        {
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
        {
            "k_threshold": skd_k_thresh if enable_k_thresh else None,
            "d_threshold": skd_d_thresh if enable_d_thresh else None,
            "enable_sell": skd_enable_sell,
            **kd_indicator,
        },
    )


def _strategy_param_expander_label(strategy_id: str, title: str, active_strategies: list[str]) -> str:
    marker = "✅" if strategy_id in active_strategies else "⬜"
    return f"{marker} {title}"


def _reset_strategy_d(user_id: str, prefs: dict, sd: dict) -> None:
    prefs.update({
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
    })
    save_preferences(user_id, prefs)
    st.rerun()


def _reset_strategy_kd(user_id: str, prefs: dict, skd: dict) -> None:
    prefs.update({
        "skd_enable_k_thresh": False,
        "skd_k_threshold": skd.get("k_threshold") or 30,
        "skd_enable_d_thresh": False,
        "skd_d_threshold": skd.get("d_threshold") or 70,
        "skd_enable_sell": skd.get("enable_sell", True),
    })
    save_preferences(user_id, prefs)
    st.rerun()
