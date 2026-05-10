import pandas as pd

from src.data import price_fetcher


def test_fetch_prices_returns_cached_data(monkeypatch):
    cached = pd.DataFrame(
        {
            "date": ["2026-05-01"],
            "open": [1],
            "high": [2],
            "low": [1],
            "close": [2],
            "volume": [100],
        }
    )
    calls = {}

    def fake_get_price_cache(key, ttl_override=None):
        calls["key"] = key
        calls["ttl_override"] = ttl_override
        return cached

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 123)
    monkeypatch.setattr(price_fetcher, "get_price_cache", fake_get_price_cache)
    monkeypatch.setattr(
        price_fetcher.yf,
        "download",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("download called")),
    )

    result = price_fetcher.fetch_prices("TSLA", period="1Y")

    assert result.equals(cached)
    assert calls == {"key": "TSLA_1y_daily", "ttl_override": 123}


def test_fetch_prices_saves_downloaded_data(monkeypatch):
    raw = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-05-01"]),
            "Open": [1],
            "High": [2],
            "Low": [1],
            "Close": [2],
            "Volume": [100],
        }
    ).set_index("Date")
    saved = {}

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 456)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(price_fetcher.yf, "download", lambda *args, **kwargs: raw)
    monkeypatch.setattr(
        price_fetcher,
        "save_price_cache",
        lambda key, df: saved.update({"key": key, "df": df}),
    )

    result = price_fetcher.fetch_prices("TSLA", period="1Y")

    assert result["date"].tolist() == ["2026-05-01"]
    assert saved["key"] == "TSLA_1y_daily"
    assert saved["df"].equals(result)


def test_fetch_prices_falls_back_to_two_when_tw_has_no_data(monkeypatch):
    raw = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-05-01"]),
            "Open": [1],
            "High": [2],
            "Low": [1],
            "Close": [2],
            "Volume": [100],
        }
    ).set_index("Date")
    downloads = []
    saved = {}
    resolutions = {}

    def fake_download(ticker, *args, **kwargs):
        downloads.append(ticker)
        return pd.DataFrame() if ticker == "3081.TW" else raw

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 456)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(price_fetcher, "get_resolved_ticker", lambda ticker: None)
    monkeypatch.setattr(price_fetcher.yf, "download", fake_download)
    monkeypatch.setattr(
        price_fetcher,
        "save_price_cache",
        lambda key, df: saved.update({"key": key, "df": df}),
    )
    monkeypatch.setattr(
        price_fetcher,
        "save_ticker_resolution",
        lambda ticker, resolved: resolutions.update({ticker: resolved}),
    )

    result = price_fetcher.fetch_prices("3081.TW", period="1Y")

    assert downloads == ["3081.TW", "3081.TWO"]
    assert result["date"].tolist() == ["2026-05-01"]
    assert saved["key"] == "3081.TWO_1y_daily"
    assert resolutions == {"3081.TW": "3081.TWO"}


def test_fetch_prices_uses_cached_two_resolution_before_trying_tw(monkeypatch):
    raw = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-05-01"]),
            "Open": [1],
            "High": [2],
            "Low": [1],
            "Close": [2],
            "Volume": [100],
        }
    ).set_index("Date")
    downloads = []

    def fake_download(ticker, *args, **kwargs):
        downloads.append(ticker)
        return raw

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 456)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(price_fetcher, "get_resolved_ticker", lambda ticker: "3081.TWO")
    monkeypatch.setattr(price_fetcher.yf, "download", fake_download)
    monkeypatch.setattr(price_fetcher, "save_price_cache", lambda key, df: None)
    monkeypatch.setattr(price_fetcher, "save_ticker_resolution", lambda ticker, resolved: None)

    result = price_fetcher.fetch_prices("3081.TW", period="1Y")

    assert result["date"].tolist() == ["2026-05-01"]
    assert downloads == ["3081.TWO"]


def test_fetch_prices_keeps_tw_when_tw_has_data(monkeypatch):
    raw = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-05-01"]),
            "Open": [1],
            "High": [2],
            "Low": [1],
            "Close": [2],
            "Volume": [100],
        }
    ).set_index("Date")
    downloads = []

    def fake_download(ticker, *args, **kwargs):
        downloads.append(ticker)
        return raw

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 456)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(price_fetcher, "get_resolved_ticker", lambda ticker: None)
    monkeypatch.setattr(price_fetcher.yf, "download", fake_download)
    monkeypatch.setattr(price_fetcher, "save_price_cache", lambda key, df: None)
    monkeypatch.setattr(price_fetcher, "save_ticker_resolution", lambda ticker, resolved: None)

    result = price_fetcher.fetch_prices("2330.TW", period="1Y")

    assert result["date"].tolist() == ["2026-05-01"]
    assert downloads == ["2330.TW"]


def test_fetch_quote_uses_quote_ttl(monkeypatch):
    cached = pd.DataFrame(
        {
            "date": ["2026-05-01"],
            "open": [1],
            "high": [2],
            "low": [1],
            "close": [2],
            "volume": [100],
        }
    )
    calls = {}

    def fake_cache_ttl_seconds(ticker, granularity):
        calls["granularity"] = granularity
        return 60

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", fake_cache_ttl_seconds)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: cached)

    result = price_fetcher.fetch_quote("TSLA")

    assert result.equals(cached)
    assert calls["granularity"] == "quote"


def test_fetch_prices_by_interval_uses_intraday_ttl_and_preserves_time(monkeypatch):
    raw = pd.DataFrame(
        {
            "Datetime": pd.to_datetime(["2026-05-01 09:30", "2026-05-01 09:31"]),
            "Open": [1, 2],
            "High": [2, 3],
            "Low": [1, 2],
            "Close": [2, 3],
            "Volume": [100, 200],
        }
    ).set_index("Datetime")
    calls = {}

    def fake_cache_ttl_seconds(ticker, granularity):
        calls["granularity"] = granularity
        return 60

    monkeypatch.setattr(price_fetcher, "cache_ttl_seconds", fake_cache_ttl_seconds)
    monkeypatch.setattr(price_fetcher, "get_price_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(price_fetcher.yf, "download", lambda *args, **kwargs: raw)
    monkeypatch.setattr(price_fetcher, "save_price_cache", lambda key, df: None)

    result = price_fetcher.fetch_prices_by_interval("TSLA", "1m", period="1M")

    assert calls["granularity"] == "intraday"
    assert result["date"].tolist() == ["2026-05-01 09:30", "2026-05-01 09:31"]
