import pandas as pd

from src.ui.components.categorized_watchlist import build_watchlist_table
from src.ui.components.intraday_tick_chart import build_intraday_tick_chart


def test_build_watchlist_table_uses_quote_summary(monkeypatch):
    import src.ui.components.categorized_watchlist as module

    monkeypatch.setattr(
        module,
        "_quote_summary",
        lambda ticker: {"close": 100, "change": 1, "change_pct": 1.0, "volume": 2000},
    )

    df = build_watchlist_table([{"ticker": "tsla", "name": "Tesla"}])

    assert df.iloc[0]["代碼"] == "TSLA"
    assert df.iloc[0]["成交"] == 100


def test_build_intraday_tick_chart_returns_line_trace():
    df = pd.DataFrame({"date": ["2026-05-01 09:30"], "close": [100]})

    fig = build_intraday_tick_chart(df, "TSLA")

    assert len(fig.data) == 1
    assert fig.data[0].name == "1m"
