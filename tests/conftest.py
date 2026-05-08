import pandas as pd
import numpy as np
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def clear_streamlit_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """60 rows of synthetic OHLCV data with lowercase columns."""
    np.random.seed(42)
    n = 60
    close = 100 + np.cumsum(np.random.randn(n))
    high  = close + np.abs(np.random.randn(n)) * 0.5
    low   = close - np.abs(np.random.randn(n)) * 0.5
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "date":   dates.strftime("%Y-%m-%d"),
        "open":   close - np.random.randn(n) * 0.3,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": np.random.randint(1_000_000, 5_000_000, n),
    })
