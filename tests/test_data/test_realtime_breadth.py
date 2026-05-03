from src.data.index_fetcher import parse_realtime_breadth_rows


def test_parse_realtime_breadth_rows_extracts_buy_sell_ratio():
    result = parse_realtime_breadth_rows([
        {
            "時間": "09:30",
            "AccBidVolume": "1,200",
            "AccAskVolume": "800",
        }
    ])

    assert result["available"] is True
    assert result["buy_orders_lots"] == 1200
    assert result["sell_orders_lots"] == 800
    assert result["buy_sell_diff"] == 400
    assert result["ratio"] == 1.5
