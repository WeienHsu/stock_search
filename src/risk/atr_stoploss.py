import pandas as pd

from src.indicators.atr import add_atr


def compute_atr_stoploss(
    df: pd.DataFrame,
    entry_price: float,
    atr_period: int = 14,
    atr_multiplier: float = 2.0,
) -> dict:
    """
    Compute ATR-based dynamic stop-loss for a given entry price.

    Returns:
        atr_value, stop_price, risk_per_share (entry - stop)
    """
    df = add_atr(df, period=atr_period)
    col = f"atr_{atr_period}"
    atr_value = float(df[col].iloc[-1])
    stop_price = entry_price - atr_multiplier * atr_value
    risk_per_share = entry_price - stop_price

    return {
        "atr_value": round(atr_value, 4),
        "stop_price": round(stop_price, 4),
        "risk_per_share": round(risk_per_share, 4),
        "atr_multiplier": atr_multiplier,
    }
