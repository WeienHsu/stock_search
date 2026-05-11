import pandas as pd

from src.indicators.ma import add_ma
from src.ui.charts.kline_chart import SignalLayer, build_combined_chart


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
    profile_texts = [str(annotation.text) for annotation in fig.layout.annotations if "POC" in str(annotation.text) or "VP" in str(annotation.text)]
    assert profile_texts
    assert all("估算買壓" not in text and "估算賣壓" not in text for text in profile_texts)


def test_build_combined_chart_can_hide_signal_markers():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5, freq="B").strftime("%Y-%m-%d"),
        "open": [100, 101, 102, 103, 104],
        "high": [101, 102, 103, 104, 105],
        "low": [99, 100, 101, 102, 103],
        "close": [100, 101, 102, 103, 104],
        "volume": [1000, 1100, 1200, 1300, 1400],
    })
    df = add_ma(df, [5])
    signal_date = df["date"].iloc[-1]

    fig = build_combined_chart(
        df,
        "TEST",
        ma_periods=[5],
        signal_dates=[],
        bias_period=20,
        show_macd=False,
        show_kd=False,
        show_bias=False,
        signal_layers=[
            SignalLayer(
                strategy_id="strategy_d",
                label="Strategy D",
                buy_dates=[signal_date],
                sell_dates=[],
            )
        ],
        show_signals=False,
    )

    annotation_texts = [str(annotation.text) for annotation in fig.layout.annotations]
    assert "▼" not in annotation_texts


def test_build_combined_chart_overlays_volume_on_price_panel():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=5, freq="B").strftime("%Y-%m-%d"),
        "open": [100, 101, 102, 103, 104],
        "high": [101, 102, 103, 104, 105],
        "low": [99, 100, 101, 102, 103],
        "close": [100, 101, 102, 103, 104],
        "volume": [1000, 1100, 1200, 1300, 1400],
    })
    df = add_ma(df, [5])

    fig = build_combined_chart(
        df,
        "TEST",
        ma_periods=[5],
        signal_dates=[],
        bias_period=20,
        show_macd=False,
        show_kd=False,
        show_bias=False,
        show_volume_bar=True,
    )

    assert fig.layout.meta["panels"] == ["main"]
    assert fig.layout.meta["ma_periods"] == [5]
    assert fig.layout.meta["volume_overlay_axis"] == "yaxis99"
    assert fig.layout.yaxis99.showticklabels is False
    volume_trace = next(trace for trace in fig.data if trace.name == "成交量")
    assert volume_trace.yaxis == "y99"
    assert volume_trace.opacity == 0.28
    assert volume_trace.hoverinfo == "none"
    assert next(trace for trace in fig.data if trace.name == "K線").hoverinfo == "none"
    assert next(trace for trace in fig.data if trace.name == "MA5").hoverinfo == "none"


def test_build_combined_chart_can_show_volume_profile_delta_labels():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=20, freq="B").strftime("%Y-%m-%d"),
        "open": [100 + i for i in range(20)],
        "high": [102 + i for i in range(20)],
        "low": [99 + i for i in range(20)],
        "close": [101.8 + i for i in range(20)],
        "volume": [1000 + i * 20 for i in range(20)],
    })
    df = add_ma(df, [5])

    fig = build_combined_chart(
        df,
        "TEST",
        ma_periods=[5],
        signal_dates=[],
        bias_period=20,
        show_macd=False,
        show_kd=False,
        show_bias=False,
        show_volume_profile=True,
        show_volume_profile_delta=True,
    )

    profile_texts = [str(annotation.text) for annotation in fig.layout.annotations if "POC" in str(annotation.text) or "VP" in str(annotation.text)]
    assert any("估算買壓" in text for text in profile_texts)
    assert fig.layout.margin.r >= 230
