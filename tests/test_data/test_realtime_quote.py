from src.data.realtime_quote import parse_mis_row


def _row(**overrides):
    base = {
        "c": "2330",
        "n": "台積電",
        "ex": "tse",
        "z": "1080.0000",
        "y": "1075.0000",
        "o": "1076.0000",
        "h": "1085.0000",
        "l": "1072.0000",
        "v": "25000",
        "tlong": "1718084400000",
    }
    base.update(overrides)
    return base


def test_parse_mis_row_basic():
    quote = parse_mis_row(_row())
    assert quote["symbol"] == "2330.TW"
    assert quote["name"] == "台積電"
    assert quote["price"] == 1080.0
    assert quote["prev_close"] == 1075.0
    assert quote["change"] == 5.0
    assert quote["change_pct"] == 0.47
    assert quote["market"] == "TW"
    assert quote["ts"] == 1718084400


def test_parse_mis_row_otc_suffix():
    assert parse_mis_row(_row(ex="otc", c="5483"))["symbol"] == "5483.TWO"


def test_parse_mis_row_no_trade_falls_back_to_bid():
    quote = parse_mis_row(_row(z="-", b="1079.0000_1078.0000_1077.0000"))
    assert quote["price"] == 1079.0


def test_parse_mis_row_no_trade_no_bid_falls_back_to_prev_close():
    quote = parse_mis_row(_row(z="-", b="-"))
    assert quote["price"] == 1075.0


def test_parse_mis_row_missing_code_returns_none():
    assert parse_mis_row({"n": "x"}) is None
