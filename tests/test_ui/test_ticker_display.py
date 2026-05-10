from src.ui.utils import ticker_display


def test_resolved_display_ticker_uses_resolution_when_available(monkeypatch):
    monkeypatch.setattr(ticker_display, "get_resolved_ticker", lambda ticker: "3081.TWO")

    assert ticker_display.resolved_display_ticker("3081") == "3081.TWO"


def test_resolved_display_ticker_falls_back_to_normalized_ticker(monkeypatch):
    monkeypatch.setattr(ticker_display, "get_resolved_ticker", lambda ticker: None)

    assert ticker_display.resolved_display_ticker("2330") == "2330.TW"
    assert ticker_display.resolved_display_ticker("tsla") == "TSLA"


def test_should_sync_display_ticker_only_when_suffix_changes():
    assert ticker_display.should_sync_display_ticker("3081", "3081.TWO") is True
    assert ticker_display.should_sync_display_ticker("2330", "2330.TW") is False
