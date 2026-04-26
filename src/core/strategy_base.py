from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import pandas as pd


@dataclass
class Signal:
    date: str
    signal_type: str        # "buy" | "sell" | "neutral"
    strategy_id: str
    strength: float = 1.0   # 0.0–1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyBase(ABC):
    """All strategies must implement this interface."""

    strategy_id: str = ""

    @abstractmethod
    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        """
        Run strategy on price DataFrame and return signals.

        df must have lowercase columns: close, high, low, open, volume,
        and a 'date' column (or DatetimeIndex).
        """

    @abstractmethod
    def default_params(self) -> dict[str, Any]:
        """Return default parameter dict for this strategy."""
