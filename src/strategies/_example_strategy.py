"""
Template for adding a new strategy.

Steps:
1. Copy this file to src/strategies/strategy_e.py (or your name)
2. Set strategy_id to a unique string
3. Implement default_params() and compute()
4. Call register("your_id", YourStrategy) at the bottom
"""
from typing import Any
import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register


class ExampleStrategy(StrategyBase):
    strategy_id = "example"

    def default_params(self) -> dict[str, Any]:
        return {"param_a": 10}

    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        return []


# register("example", ExampleStrategy)  # uncomment to activate
