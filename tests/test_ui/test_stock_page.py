from pathlib import Path

import pandas as pd

from src.ui.pages import stock_page
from src.ui.pages.stock_page import _chart_indicator_flags


def test_chart_indicator_flags_follow_settings_preferences():
    cfg = {
        "show_macd": True,
        "show_kd": True,
        "show_bias": False,
        "show_volume_bar": True,
        "show_volume_profile": True,
        "show_candlestick_patterns": False,
        "show_ma_cross_labels": True,
    }
    chart_df = pd.DataFrame({"histogram": [1], "K": [50]})

    assert _chart_indicator_flags(cfg, chart_df) == {
        "show_macd": True,
        "show_kd": True,
        "show_bias": False,
        "show_volume_bar": True,
        "show_volume_profile": True,
        "show_candlestick_patterns": False,
        "show_ma_cross_labels": True,
    }


def test_chart_indicator_flags_require_indicator_columns():
    cfg = {"show_macd": True, "show_kd": True}

    result = _chart_indicator_flags(cfg, pd.DataFrame({"close": [100]}))

    assert result["show_macd"] is False
    assert result["show_kd"] is False


def test_stock_page_uses_chart_empty_state_for_missing_price_data():
    source = Path(stock_page.__file__).read_text(encoding="utf-8")

    assert "render_empty_state" in source
    assert '"無法取得價格資料"' in source
