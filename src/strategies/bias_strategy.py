from typing import Any
import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register
from src.indicators.bias import add_bias


class BiasStrategy(StrategyBase):
    """
    Bias-based signal:
    - Buy when bias drops below buy_threshold (oversold)
    - Sell when bias rises above sell_threshold (overbought)
    """
    strategy_id = "bias"

    def default_params(self) -> dict[str, Any]:
        return {
            "period": 20,
            "buy_threshold": -5.0,
            "sell_threshold": 5.0,
        }

    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        p = {**self.default_params(), **params}
        period = p["period"]
        df = add_bias(df, period=period)
        col = f"bias_{period}"

        signals: list[Signal] = []
        for _, row in df.iterrows():
            val = row.get(col)
            if pd.isna(val):
                continue
            date_val = str(row["date"])[:10] if "date" in row.index else ""
            if val <= p["buy_threshold"]:
                signals.append(Signal(
                    date=date_val,
                    signal_type="buy",
                    strategy_id=self.strategy_id,
                    strength=min(abs(val) / abs(p["buy_threshold"]), 1.0),
                    metadata={"bias": round(float(val), 2), "period": period},
                ))
            elif val >= p["sell_threshold"]:
                signals.append(Signal(
                    date=date_val,
                    signal_type="sell",
                    strategy_id=self.strategy_id,
                    strength=min(val / p["sell_threshold"], 1.0),
                    metadata={"bias": round(float(val), 2), "period": period},
                ))
        return signals


register("bias", BiasStrategy)
