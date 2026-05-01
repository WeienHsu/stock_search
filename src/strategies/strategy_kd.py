from typing import Any

import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register
from src.indicators.kd import add_kd, kd_golden_cross, kd_death_cross

# Morandi-compatible colors distinct from Strategy D's gold/blue
KD_BUY_COLOR = "#6A9E8A"   # sage teal
KD_SELL_COLOR = "#C87D6A"  # terracotta


class StrategyKD(StrategyBase):
    """KD-only strategy: golden cross = buy, death cross = sell.

    Optional threshold gates keep signals in low/high KD zones only.
    No MACD filter — fires on every cross (or gated cross) in the data.
    """

    strategy_id = "strategy_kd"

    def default_params(self) -> dict[str, Any]:
        return {
            "k_threshold": None,   # None = no gate; int = K must be below for golden cross
            "d_threshold": None,   # None = no gate; int = K must be above for death cross
            "enable_sell": True,
            "kd_k": 9,
            "kd_d": 3,
            "kd_smooth_k": 3,
        }

    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        p = {**self.default_params(), **params}
        try:
            df = add_kd(df, k=p["kd_k"], d=p["kd_d"], smooth_k=p["kd_smooth_k"])
        except ValueError:
            return []

        k_thresh = p.get("k_threshold") or None
        d_thresh = p.get("d_threshold") or None

        buy_mask = kd_golden_cross(df, k_threshold=k_thresh)
        signals: list[Signal] = []
        for _, row in df[buy_mask].iterrows():
            signals.append(Signal(
                date=str(row["date"])[:10],
                signal_type="buy",
                strategy_id=self.strategy_id,
                strength=max(0.0, min(1.0, 1.0 - float(row.get("K", 50)) / 100)),
                metadata={"K": float(row.get("K", 0)), "D": float(row.get("D", 0))},
            ))

        if p.get("enable_sell", True):
            sell_mask = kd_death_cross(df, d_threshold=d_thresh)
            for _, row in df[sell_mask].iterrows():
                signals.append(Signal(
                    date=str(row["date"])[:10],
                    signal_type="sell",
                    strategy_id=self.strategy_id,
                    strength=max(0.0, min(1.0, float(row.get("K", 50)) / 100)),
                    metadata={"K": float(row.get("K", 0)), "D": float(row.get("D", 0))},
                ))

        return sorted(signals, key=lambda s: s.date)


register("strategy_kd", StrategyKD)
