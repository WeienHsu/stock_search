import os

# Force sqlite before any src import: server.main calls load_dotenv(), and a
# developer .env may point STORAGE_BACKEND at a real Postgres instance.
# load_dotenv never overrides variables that are already set.
os.environ["STORAGE_BACKEND"] = "sqlite"

import pandas as pd
import numpy as np
import pytest

from src.core.ttl_cache import clear_all_ttl_caches


@pytest.fixture(autouse=True)
def _clear_ttl_caches():
    clear_all_ttl_caches()
    yield
    clear_all_ttl_caches()


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
