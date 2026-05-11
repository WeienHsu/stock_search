import pandas as pd

from src.ui.charts._ohlc_hover import build_ohlc_hover_script, build_ohlc_rows


def test_build_ohlc_rows_formats_latest_status_values_and_ma_values():
    df = pd.DataFrame({
        "date": ["2026-05-01", "2026-05-02"],
        "open": [100.0, 104.0],
        "high": [105.0, 108.0],
        "low": [99.0, 103.0],
        "close": [104.0, 102.0],
        "volume": [1000, 2500],
        "MA_5": [101.0, 102.5],
        "MA_20": [98.0, 99.5],
    })

    rows = build_ohlc_rows(df, ma_periods=[20, 5, 60], ma_colors={5: "#AA5500", 20: "#0055AA"})

    assert rows[0]["change"] == "+4.00"
    assert rows[0]["changePct"] == "+4.00%"
    assert rows[0]["tone"] == "up"
    assert rows[1]["change"] == "-2.00"
    assert rows[1]["changePct"] == "-1.92%"
    assert rows[1]["volume"] == "2,500"
    assert rows[1]["tone"] == "down"
    assert rows[1]["ma"] == [
        {"label": "MA5", "value": "102.50", "color": "#AA5500"},
        {"label": "MA20", "value": "99.50", "color": "#0055AA"},
    ]


def test_build_ohlc_hover_script_creates_status_bar_and_hover_handler():
    script = build_ohlc_hover_script(
        "chart_1",
        [{"key": "2026-05-01", "date": "2026-05-01", "open": "100.00", "high": "105.00", "low": "99.00", "close": "104.00", "change": "+4.00", "changePct": "+4.00%", "volume": "1,000", "tone": "up"}],
        up_color="#AA0000",
        down_color="#008800",
        neutral_color="#666666",
        background_color="#FAFAFA",
        border_color="#DDDDDD",
    )

    assert "stock-ohlc-status" in script
    assert "plotly_hover" in script
    assert "開" in script
    assert "高" in script
    assert "低" in script
    assert "收" in script
    assert "量" in script
    assert "plotly_unhover" in script
    assert "mouseleave" in script
    assert "status.classList.add(\"is-visible\")" in script
    assert "status.classList.remove(\"is-visible\")" in script
    assert "render(rows[rows.length - 1] || null)" in script
    assert "stock-ohlc-ma" in script
    assert "stock-ohlc-row-main" in script
    assert "stock-ohlc-row-ma" in script
    assert "background: #FAFAFA" in script
    assert "border-bottom: 1px solid #DDDDDD" in script
    assert "if (item.color) maCell.style.color = item.color" in script
