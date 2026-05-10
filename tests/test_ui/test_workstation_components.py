import pandas as pd

from pathlib import Path

from src.ui.components.categorized_watchlist import build_watchlist_table, compact_watchlist_table
from src.ui.components.intraday_tick_chart import build_intraday_tick_chart
from src.ui.components import stock_detail_tabs


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


def test_build_watchlist_table_can_skip_quote_fetch(monkeypatch):
    import src.ui.components.categorized_watchlist as module

    monkeypatch.setattr(
        module,
        "_quote_summary",
        lambda ticker: (_ for _ in ()).throw(AssertionError("quote should not be fetched")),
    )

    df = build_watchlist_table([{"ticker": "2330.TW", "name": "台積電"}], include_quotes=False)

    assert df.iloc[0]["成交"] == "—"


def test_compact_watchlist_table_keeps_picker_columns_only():
    df = pd.DataFrame({
        "代碼": ["2330.TW"],
        "名稱": ["台積電"],
        "成交": ["—"],
        "漲跌": ["—"],
    })

    compact = compact_watchlist_table(df)

    assert list(compact.columns) == ["代碼", "名稱"]


def test_my_list_category_uses_existing_watchlist(monkeypatch):
    import src.ui.components.categorized_watchlist as module

    monkeypatch.setattr(module, "get_watchlist", lambda user_id: [{"ticker": "MSFT", "name": "Microsoft"}])
    monkeypatch.setattr(module, "list_items", lambda user_id, category_id: [{"ticker": "TSLA", "name": "Tesla"}])

    items = module._items_for_category("user-1", {"id": "cat-1", "name": "自選清單"})

    assert items == [{"ticker": "MSFT", "name": "Microsoft"}]


def test_workstation_uses_shared_market_strip():
    import src.ui.pages.workstation_page as module

    assert not hasattr(module, "_render_market_board")
    assert hasattr(module, "_render_market_strip")
    assert hasattr(module, "_render_watchlist_drawer")


def test_workstation_moves_categorized_watchlist_into_popover():
    import src.ui.pages.workstation_page as module

    source = Path(module.__file__).read_text(encoding="utf-8")

    assert 'st.popover("自選 / 分類"' in source
    assert "render_categorized_watchlist(user_id, compact=True)" in source


def test_build_intraday_tick_chart_returns_line_trace():
    df = pd.DataFrame({"date": ["2026-05-01 09:30"], "close": [100]})

    fig = build_intraday_tick_chart(df, "TSLA")

    assert len(fig.data) == 1
    assert fig.data[0].name == "1m"


def test_revenue_frame_for_display_uses_chinese_labels_and_latest_first():
    df = pd.DataFrame({
        "period": ["2026-03", "2026-05", "2026-04"],
        "revenue": [100.0, 120.0, 110.0],
        "yoy_pct": [1.0, 3.0, 2.0],
    })

    display = stock_detail_tabs.revenue_frame_for_display(df)

    assert list(display.columns) == ["月份", "月營收(仟元)", "年增率(%)"]
    assert display["月份"].tolist() == ["2026-05", "2026-04", "2026-03"]


def test_revenue_chart_frame_keeps_time_series_oldest_first():
    df = pd.DataFrame({
        "period": ["2026-05", "2026-03", "2026-04"],
        "revenue": [120.0, 100.0, 110.0],
    })

    chart = stock_detail_tabs.revenue_chart_frame(df)

    assert chart["月份"].tolist() == ["2026-03", "2026-04", "2026-05"]


def test_major_holder_trend_chart_uses_padded_y_axis_range():
    history = pd.DataFrame({
        "date": ["2026-05-01", "2026-05-02", "2026-05-03"],
        "foreign_holding_pct": [72.1, 72.2, 72.3],
    })

    fig = stock_detail_tabs.build_major_holder_trend_chart(history)

    assert fig.data[0].name == "外資持股比率"
    assert fig.layout.yaxis.range[0] < 72.1
    assert fig.layout.yaxis.range[1] > 72.3


def test_stock_detail_tabs_uses_stacked_chip_layout_for_narrow_workstation_column():
    source = Path(stock_detail_tabs.__file__).read_text(encoding="utf-8")

    assert 'render_chip_panel(ticker, chart_layout="stacked")' in source
