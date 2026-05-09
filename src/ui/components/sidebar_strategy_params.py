from __future__ import annotations

import streamlit as st


def build_strategy_params(defaults: dict, prefs: dict) -> tuple[dict, dict]:
    sd = defaults["strategy_d"]
    skd = defaults.get("strategy_kd", {})
    buy_kd_window = int(prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"])))
    buy_n_bars = int(prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"])))
    buy_max_viol = int(prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"])))
    buy_lookback = int(prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"])))
    buy_recovery = float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"])))
    buy_kd_thresh = int(prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"])))
    enable_sell = bool(prefs.get("enable_sell_signal", sd.get("enable_sell_signal", True)))
    sell_kd_window = int(prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"])))
    sell_n_bars = int(prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"])))
    sell_max_viol = int(prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"])))
    sell_lookback = int(prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"])))
    sell_recovery = float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"])))
    sell_kd_d_thresh = int(prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"])))

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
            "k_threshold": int(prefs.get("skd_k_threshold", skd.get("k_threshold") or 30))
            if prefs.get("skd_enable_k_thresh", False)
            else None,
            "d_threshold": int(prefs.get("skd_d_threshold", skd.get("d_threshold") or 70))
            if prefs.get("skd_enable_d_thresh", False)
            else None,
            "enable_sell": bool(prefs.get("skd_enable_sell", skd.get("enable_sell", True))),
            **kd_indicator,
        },
    )


def render_strategy_param_summary(
    defaults: dict,
    prefs: dict,
    active_strategies: list[str],
) -> None:
    strategy_d_params, strategy_kd_params = build_strategy_params(defaults, prefs)
    with st.sidebar.expander("策略參數摘要", expanded=False):
        if "strategy_d" in active_strategies:
            sell_text = "啟用" if strategy_d_params["enable_sell_signal"] else "停用"
            st.caption(
                "Strategy D："
                f"買KD≤{strategy_d_params['buy_kd_k_threshold']}、"
                f"賣KD≥{strategy_d_params['sell_kd_d_threshold']}、"
                f"賣出訊號{sell_text}"
            )
        if "strategy_kd" in active_strategies:
            k_text = strategy_kd_params["k_threshold"] if strategy_kd_params["k_threshold"] is not None else "未篩選"
            d_text = strategy_kd_params["d_threshold"] if strategy_kd_params["d_threshold"] is not None else "未篩選"
            sell_text = "啟用" if strategy_kd_params["enable_sell"] else "停用"
            st.caption(f"Strategy KD：黃金K {k_text}、死亡K {d_text}、賣出訊號{sell_text}")
        if not active_strategies:
            st.caption("目前未啟用策略訊號。")
        st.caption("請至 Settings → Strategy Defaults 調整參數。")


def _strategy_param_expander_label(strategy_id: str, title: str, active_strategies: list[str]) -> str:
    marker = "✅" if strategy_id in active_strategies else "⬜"
    return f"{marker} {title}"
