from typing import Any

from src.repositories._backends import get_user_backend

_backend = get_user_backend()
_KEY = "preferences"

_DEFAULTS: dict[str, Any] = {
    "show_macd": True,
    "show_kd": True,
    "show_bias": True,
    "show_news": True,
    "bias_period": 20,
    "ma_periods": [5, 20, 60],
    "active_strategies": ["strategy_d"],
    "default_period": "6M",
    "theme": "morandi",
    "kd_window": 10,
    "n_bars": 3,
    "recovery_pct": 0.7,
    "kd_k_threshold": 20,
    "buy_kd_window": 10,
    "buy_n_bars": 3,
    "buy_recovery_pct": 0.7,
    "buy_kd_k_threshold": 20,
    "buy_max_violations": 1,
    "buy_lookback_bars": 20,
    "sell_kd_window": 10,
    "sell_n_bars": 3,
    "sell_recovery_pct": 0.7,
    "sell_kd_d_threshold": 80,
    "sell_max_violations": 1,
    "sell_lookback_bars": 20,
}


def get_preferences(user_id: str) -> dict[str, Any]:
    saved = _backend.get(user_id, _KEY, default={})
    return {**_DEFAULTS, **saved}


def save_preferences(user_id: str, prefs: dict[str, Any]) -> None:
    _backend.save(user_id, _KEY, prefs)


def update_preference(user_id: str, key: str, value: Any) -> None:
    prefs = get_preferences(user_id)
    prefs[key] = value
    save_preferences(user_id, prefs)
