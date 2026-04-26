from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.strategy_base import StrategyBase

_registry: dict[str, type["StrategyBase"]] = {}


def register(strategy_id: str, cls: type["StrategyBase"]) -> None:
    _registry[strategy_id] = cls


def get(strategy_id: str) -> "StrategyBase":
    if strategy_id not in _registry:
        raise KeyError(f"Strategy '{strategy_id}' not registered.")
    return _registry[strategy_id]()


def list_strategies() -> list[str]:
    return list(_registry.keys())
