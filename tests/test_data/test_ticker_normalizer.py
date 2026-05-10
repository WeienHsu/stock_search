from src.data.ticker_utils import normalize_ticker, normalize_ticker_with_fallback


def test_normalize_ticker_keeps_tw_default_for_numeric_taiwan_codes():
    assert normalize_ticker("3081") == "3081.TW"
    assert normalize_ticker("2330") == "2330.TW"


def test_normalize_ticker_with_fallback_returns_tw_then_two_for_numeric_codes():
    assert normalize_ticker_with_fallback("3081") == ["3081.TW", "3081.TWO"]
    assert normalize_ticker_with_fallback("2330.TW") == ["2330.TW", "2330.TWO"]


def test_normalize_ticker_with_fallback_keeps_explicit_two_and_us_symbols():
    assert normalize_ticker_with_fallback("3081.TWO") == ["3081.TWO"]
    assert normalize_ticker_with_fallback("tsla") == ["TSLA"]
    assert normalize_ticker_with_fallback("") == []
