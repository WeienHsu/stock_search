from src.ui.sidebar import (
    _active_strategies_from_toggles,
    _normalize_saved_active_strategies,
    _sync_sidebar_ticker_state,
    _strategy_param_expander_label,
)
from src.ui.components.sidebar_strategy_params import build_strategy_params


def test_normalize_saved_active_strategies_defaults_when_missing():
    assert _normalize_saved_active_strategies(["strategy_d", "strategy_kd"], None) == ["strategy_d"]


def test_normalize_saved_active_strategies_filters_unknown_values():
    assert _normalize_saved_active_strategies(
        ["strategy_d", "strategy_kd"],
        ["strategy_kd", "legacy_strategy"],
    ) == ["strategy_kd"]


def test_active_strategies_from_toggles_allows_all_off():
    assert _active_strategies_from_toggles({"strategy_d": False, "strategy_kd": False}) == []


def test_strategy_param_expander_label_reflects_active_state():
    assert _strategy_param_expander_label("strategy_d", "Strategy D 參數", ["strategy_d"]).startswith("✅")
    assert _strategy_param_expander_label("strategy_d", "Strategy D 參數", []).startswith("⬜")


def test_sync_sidebar_ticker_state_uses_default_without_widget_value():
    session_state = {}

    _sync_sidebar_ticker_state(session_state, "2330.TW")

    assert session_state["sidebar_ticker"] == "2330.TW"
    assert "_applied_query_ticker" not in session_state


def test_sync_sidebar_ticker_state_applies_new_query_ticker():
    session_state = {"sidebar_ticker": "2330.TW", "_applied_query_ticker": "2330.TW"}

    _sync_sidebar_ticker_state(session_state, "2330.TW", "3081.TWO")

    assert session_state["sidebar_ticker"] == "3081.TWO"
    assert session_state["_applied_query_ticker"] == "3081.TWO"


def test_sync_sidebar_ticker_state_does_not_overwrite_manual_value_without_query():
    session_state = {"sidebar_ticker": "TSLA"}

    _sync_sidebar_ticker_state(session_state, "2330.TW")

    assert session_state["sidebar_ticker"] == "TSLA"


def test_build_strategy_params_reads_saved_strategy_defaults():
    defaults = {
        "strategy_d": {
            "buy_kd_window": 3,
            "buy_n_bars": 3,
            "buy_recovery_pct": 0.6,
            "buy_kd_k_threshold": 22,
            "buy_max_violations": 1,
            "buy_lookback_bars": 20,
            "sell_kd_window": 3,
            "sell_n_bars": 3,
            "sell_recovery_pct": 0.6,
            "sell_kd_d_threshold": 80,
            "sell_max_violations": 1,
            "sell_lookback_bars": 20,
            "enable_sell_signal": True,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "kd_k": 9,
            "kd_d": 3,
            "kd_smooth_k": 3,
        },
        "strategy_kd": {"k_threshold": None, "d_threshold": None, "enable_sell": True},
    }
    prefs = {
        "buy_kd_k_threshold": 25,
        "enable_sell_signal": False,
        "skd_enable_k_thresh": True,
        "skd_k_threshold": 35,
        "skd_enable_d_thresh": True,
        "skd_d_threshold": 75,
        "skd_enable_sell": False,
    }

    strategy_d, strategy_kd = build_strategy_params(defaults, prefs)

    assert strategy_d["buy_kd_k_threshold"] == 25
    assert strategy_d["enable_sell_signal"] is False
    assert strategy_kd["k_threshold"] == 35
    assert strategy_kd["d_threshold"] == 75
    assert strategy_kd["enable_sell"] is False
