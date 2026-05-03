import json

from src.data.data_source_probe import (
    parse_barchart_mmfi,
    parse_cnn_fear_greed,
    parse_json_list,
    parse_taifex_futures_html,
    parse_tpex_table,
    parse_twse_rwd_table,
)


def test_parse_twse_rwd_table():
    text = json.dumps(
        {
            "stat": "OK",
            "fields": ["證券代號", "證券名稱", "投信買賣超股數"],
            "data": [["2330", "台積電", "1,000"]],
        },
        ensure_ascii=False,
    )

    fields, rows = parse_twse_rwd_table(text)

    assert fields == ["證券代號", "證券名稱", "投信買賣超股數"]
    assert rows == [["2330", "台積電", "1,000"]]


def test_parse_json_list():
    rows = parse_json_list('[{"股票代號":"0050","融資今日餘額":"9569"}]')

    assert rows == [{"股票代號": "0050", "融資今日餘額": "9569"}]


def test_parse_tpex_table():
    text = json.dumps(
        {
            "tables": [
                {
                    "fields": ["代號", "名稱", "資餘額"],
                    "data": [["00679B", "元大美債20年", "5,116"]],
                }
            ]
        },
        ensure_ascii=False,
    )

    fields, rows = parse_tpex_table(text)

    assert fields == ["代號", "名稱", "資餘額"]
    assert rows[0][0] == "00679B"


def test_parse_cnn_fear_greed():
    text = json.dumps(
        {
            "fear_and_greed": {
                "score": 66.6,
                "rating": "greed",
                "timestamp": "2026-05-01T23:59:39+00:00",
            },
            "fear_and_greed_historical": {
                "data": [{"x": 1777507200000.0, "y": 66.6}]
            },
        }
    )

    sample = parse_cnn_fear_greed(text)

    assert sample == {
        "score": 66.6,
        "rating": "greed",
        "timestamp": "2026-05-01T23:59:39+00:00",
        "historical_points": 1,
    }


def test_parse_taifex_futures_html():
    html = """
    <table>
      <tr>
        <td>1</td><td>臺股期貨</td><td>外資</td>
        <td>70,159</td><td>554,377,821</td>
        <td>67,153</td><td>530,626,691</td>
        <td>3,006</td><td>23,751,130</td>
        <td>19,569</td><td>154,006,546</td>
        <td>63,613</td><td>500,605,400</td>
        <td>-44,044</td><td>-346,598,854</td>
      </tr>
    </table>
    """

    rows = parse_taifex_futures_html(html)

    assert rows == [
        {
            "product": "臺股期貨",
            "identity": "外資",
            "trading_long_contracts": "70,159",
            "trading_short_contracts": "67,153",
            "trading_net_contracts": "3,006",
            "open_interest_long_contracts": "19,569",
            "open_interest_short_contracts": "63,613",
            "open_interest_net_contracts": "-44,044",
        }
    ]


def test_parse_barchart_mmfi():
    html = """
    <script>
    window.__data={"currentSymbol":{"symbol":"$MMFI","lastPrice":"63.72","tradeTime":"05/01/26"}};
    </script>
    """

    sample = parse_barchart_mmfi(html)

    assert sample == {"symbol": "$MMFI", "last_price": 63.72, "trade_time": "05/01/26"}
