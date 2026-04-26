from typing import Any
from src.repositories._backends.json_backend import JsonBackend

_backend = JsonBackend()
_KEY = "risk_settings"

_DEFAULTS: dict[str, Any] = {
    "max_risk_per_trade_pct": 1.0,   # % of portfolio
    "atr_multiplier": 2.0,
    "portfolio_size": 100000,
}


def get_risk_settings(user_id: str) -> dict[str, Any]:
    saved = _backend.get(user_id, _KEY, default={})
    return {**_DEFAULTS, **saved}


def save_risk_settings(user_id: str, settings: dict[str, Any]) -> None:
    _backend.save(user_id, _KEY, settings)
