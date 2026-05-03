import pandas as pd

from src.indicators.ma import add_ma
from src.ui.charts.kline_chart import build_combined_chart


def test_build_combined_chart_adds_p25_overlays():
    n = 250
    df = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
        "open": [100 + i * 0.1 for i in range(n)],
        "high": [101 + i * 0.1 for i in range(n)],
        "low": [99 + i * 0.1 for i in range(n)],
        "close": [100.5 + i * 0.1 for i in range(n)],
        "volume": [1000 + i for i in range(n)],
    })
    df.loc[n - 2, ["open", "high", "low", "close"]] = [10.0, 10.2, 8.5, 9.0]
    df.loc[n - 1, ["open", "high", "low", "close"]] = [8.8, 11.4, 8.6, 11.2]
    df = add_ma(df, [5, 10, 20, 60, 120, 240])

    fig = build_combined_chart(
        df,
        "TEST",
        ma_periods=[5, 10, 20, 60, 120, 240],
        signal_dates=[],
        bias_period=20,
        show_macd=False,
        show_kd=False,
        show_bias=False,
        show_candlestick_patterns=True,
        show_volume_profile=True,
        granularity="1wk",
        ma_cross_events=[{
            "date": df["date"].iloc[-1],
            "type": "golden_cross",
            "fast_period": 20,
            "slow_period": 60,
            "price": float(df["close"].iloc[-1]),
        }],
    )

    names = {trace.name for trace in fig.data if trace.name}
    assert "MA240" in names
    assert "MA交叉標註" in names
    assert any(str(name).startswith("K線形態") for name in names)
    assert len(fig.layout.shapes or []) >= 1
    assert "(1wk)" in str(fig.layout.annotations[0].text)
