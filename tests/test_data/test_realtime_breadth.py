from src.data.index_fetcher import parse_realtime_breadth_rows


def test_parse_realtime_breadth_rows_extracts_buy_sell_ratio():
    result = parse_realtime_breadth_rows([
        {
            "時間": "09:30",
            "累積委託買進數量": "1,200",
            "累積委託賣出數量": "800",
        }
    ])

    assert result["available"] is True
    assert result["buy_orders_lots"] == 1200
    assert result["sell_orders_lots"] == 800
    assert result["buy_sell_diff"] == 400
    assert result["ratio"] == 1.5
