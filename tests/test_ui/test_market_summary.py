import pandas as pd

from src.ui.components.market_summary import render_breadth_metric, render_index_metric


class MetricRecorder:
    def __init__(self):
        self.calls = []

    def metric(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_render_index_metric_uses_snapshot_values():
    container = MetricRecorder()
    df = pd.DataFrame({
        "date": ["2026-04-29", "2026-04-30"],
        "close": [100, 105],
        "volume": [1000, 1000],
    })

    render_index_metric(container, "TAIEX", df)

    assert container.calls[0][0] == ("TAIEX", "105.00", "5.00%")


def test_render_breadth_metric_uses_buy_sell_diff_and_ratio():
    container = MetricRecorder()

    render_breadth_metric(container, {"available": True, "buy_sell_diff": 1234, "ratio": 1.25})

    assert container.calls[0][0] == ("即時委買賣差", "1,234", "ratio 1.25")
