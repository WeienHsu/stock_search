import pandas as pd
import pytest
from src.backtest.metrics import compute_metrics


def _make_bt(returns: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "date": [f"2025-01-{i+1:02d}" for i in range(len(returns))],
        "forward_return_pct": returns,
        "win": [r > 0 for r in returns],
    })


def test_empty_returns_zeros():
    m = compute_metrics(pd.DataFrame())
    assert m["count"] == 0
    assert m["win_rate"] == 0.0


def test_win_rate():
    m = compute_metrics(_make_bt([5.0, -2.0, 3.0, -1.0]))
    assert m["win_rate"] == 50.0
    assert m["count"] == 4


def test_all_wins():
    m = compute_metrics(_make_bt([2.0, 3.0, 1.5]))
    assert m["win_rate"] == 100.0
    assert m["max_drawdown_pct"] == 0.0


def test_mdd_negative():
    m = compute_metrics(_make_bt([-5.0, -3.0, -2.0]))
    assert m["max_drawdown_pct"] < 0


def test_sharpe_positive_mean():
    m = compute_metrics(_make_bt([3.0, 2.5, 4.0, 3.5]))
    assert m["sharpe"] > 0
