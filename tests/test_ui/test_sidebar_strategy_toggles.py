from src.ui.sidebar import (
    _active_strategies_from_toggles,
    _normalize_saved_active_strategies,
    _strategy_param_expander_label,
)


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
