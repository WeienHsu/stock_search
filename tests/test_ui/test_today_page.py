import pandas as pd

from src.ui.pages.today_page import _session_pill_kind, _signal_counts, _today_table


def test_signal_counts_counts_neutral_rows_without_double_subtracting():
    df = pd.DataFrame({
        "buy_signal": [True, False, False, True],
        "sell_signal": [False, True, False, True],
    })

    assert _signal_counts(df) == {"buy": 2, "sell": 2, "neutral": 1}


def test_today_table_sorts_signal_rows_first():
    result = pd.DataFrame({
        "ticker": ["B", "A"],
        "name": ["Beta", "Alpha"],
        "current_close": [10, 20],
        "buy_status": ["⚪ 無訊號", "▲ 買進觸發"],
        "sell_status": ["⚪ 無訊號", "⚪ 無訊號"],
        "buy_signal": [False, True],
        "sell_signal": [False, False],
        "ma_bullish_score": [4, 1],
        "poc_distance_pct": [0.1, 0.2],
    })

    table = _today_table(result)

    assert table.iloc[0]["代號"] == "A"


def test_session_pill_kind_maps_market_states():
    assert _session_pill_kind("盤中") == "buy"
    assert _session_pill_kind("休市") == "neutral"
    assert _session_pill_kind("盤後") == "info"
