import numpy as np
import pandas as pd
import pytest

from src.risk.atr_stoploss import compute_atr_stoploss
from src.risk.position_sizer import compute_position_size


@pytest.fixture
def price_df():
    np.random.seed(0)
    n = 30
    close = 100 + np.cumsum(np.random.randn(n) * 0.3)
    return pd.DataFrame({
        "close": close,
        "high":  close + 0.5,
        "low":   close - 0.5,
        "open":  close,
    })


def test_atr_stoploss_below_entry(price_df):
    result = compute_atr_stoploss(price_df, entry_price=105.0)
    assert result["stop_price"] < 105.0
    assert result["risk_per_share"] > 0
    assert result["atr_value"] > 0


def test_position_sizer_basic():
    pos = compute_position_size(
        portfolio_size=100_000,
        max_risk_pct=1.0,
        risk_per_share=2.0,
        entry_price=50.0,
    )
    assert pos["shares"] == 500        # 1000 risk / 2 per share
    assert pos["position_value"] == 25_000.0
    assert pos["actual_risk_amount"] == 1_000.0


def test_position_sizer_zero_risk():
    pos = compute_position_size(100_000, 1.0, 0.0, 50.0)
    assert pos["shares"] == 0
