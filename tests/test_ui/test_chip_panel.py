import pandas as pd

from src.ui.components import chip_panel


def test_institutional_flow_chart_contains_foreign_and_investment_traces():
    df = pd.DataFrame({
        "date": ["2026-04-29", "2026-04-30"],
        "foreign_net_lots": [100, -50],
        "investment_trust_net_lots": [20, 30],
    })

    fig = chip_panel._institutional_flow_chart(df)

    assert {trace.name for trace in fig.data} == {"外資", "投信"}


def test_institutional_flow_chart_uses_shared_up_down_palette(monkeypatch):
    import src.ui.theme.plotly_template as plotly_module

    monkeypatch.setattr(plotly_module, "get_current_theme", lambda: "morandi")
    palette = plotly_module.get_chart_palette("morandi")
    df = pd.DataFrame({
        "date": ["2026-04-29", "2026-04-30"],
        "foreign_net_lots": [100, -50],
        "investment_trust_net_lots": [20, -30],
    })

    fig = chip_panel._institutional_flow_chart(df)

    assert list(fig.data[0].marker.color) == [palette.MORANDI_UP, palette.MORANDI_DOWN]
    assert list(fig.data[1].marker.color) == [palette.MORANDI_UP, palette.MORANDI_DOWN]


def test_margin_trend_chart_contains_margin_trace():
    df = pd.DataFrame({
        "date": ["2026-04-29", "2026-04-30"],
        "margin_balance": [1000, 1100],
        "short_balance": [20, 25],
    })

    fig = chip_panel._margin_trend_chart(df)

    assert "融資餘額" in {trace.name for trace in fig.data}
    assert "融券餘額" in {trace.name for trace in fig.data}


def test_lots_text_formats_large_values():
    assert chip_panel._lots_text(23_000) == "+2.30萬張"
    assert chip_panel._lots_text(-1200) == "-1,200張"


def test_lots_text_uses_dash_for_missing_values():
    assert chip_panel._lots_text(None) == "—"
    assert chip_panel._latest_numeric(pd.DataFrame(), "foreign_net_lots", default=None) is None
