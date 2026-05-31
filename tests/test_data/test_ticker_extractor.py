from src.data.ticker_extractor import extract_tickers_from_csv, extract_tickers_from_text


def test_extract_tickers_from_text_normalizes_and_fills_names():
    result = extract_tickers_from_text("我手上有 2330, 2317, TSLA")

    assert result == [
        {"ticker": "2330.TW", "name": "台積電"},
        {"ticker": "2317.TW", "name": "鴻海"},
        {"ticker": "TSLA", "name": "Tesla"},
    ]


def test_extract_tickers_from_text_ignores_duplicates_and_noise():
    result = extract_tickers_from_text("觀察：2330；雜訊文字；2330.TW；NVDA；tsla；hello!")

    assert result == [
        {"ticker": "2330.TW", "name": "台積電"},
        {"ticker": "NVDA", "name": "NVIDIA"},
        {"ticker": "TSLA", "name": "Tesla"},
    ]


def test_extract_tickers_from_csv_reads_common_headers():
    csv_text = "ticker,name\n2330,台積電自訂\nTSLA,Tesla自訂\n"

    result = extract_tickers_from_csv(csv_text)

    assert result == [
        {"ticker": "2330.TW", "name": "台積電自訂"},
        {"ticker": "TSLA", "name": "Tesla自訂"},
    ]


def test_extract_tickers_from_csv_reads_chinese_headers():
    csv_text = "代碼,名稱\n2317,鴻海自訂\n"

    assert extract_tickers_from_csv(csv_text) == [{"ticker": "2317.TW", "name": "鴻海自訂"}]
