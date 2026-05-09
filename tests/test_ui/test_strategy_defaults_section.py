from src.ui.pages.settings.strategy_defaults_section import (
    _strategy_d_default_values,
    _strategy_kd_default_values,
)


def test_strategy_d_default_values_include_sell_toggle():
    defaults = {
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
        "enable_sell_signal": False,
    }

    result = _strategy_d_default_values(defaults)

    assert result["enable_sell_signal"] is False
    assert result["buy_kd_k_threshold"] == 22


def test_strategy_kd_default_values_reset_filters_to_disabled():
    result = _strategy_kd_default_values({"k_threshold": None, "d_threshold": None, "enable_sell": True})

    assert result == {
        "skd_enable_k_thresh": False,
        "skd_k_threshold": 30,
        "skd_enable_d_thresh": False,
        "skd_d_threshold": 70,
        "skd_enable_sell": True,
    }
