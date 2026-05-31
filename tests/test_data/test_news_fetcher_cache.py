from src.data import news_fetcher


def test_fetch_news_returns_cached_articles_with_news_ttl(monkeypatch):
    cached = [{"headline": "cached"}]
    calls = {}

    def fake_get_news_cache(ticker, ttl_override=None):
        calls["ticker"] = ticker
        calls["ttl_override"] = ttl_override
        return cached

    monkeypatch.setattr(news_fetcher, "cache_ttl_seconds", lambda ticker, granularity: 300)
    monkeypatch.setattr(news_fetcher, "get_news_cache", fake_get_news_cache)
    monkeypatch.setattr(
        news_fetcher,
        "resolve_api_key",
        lambda user_id: (_ for _ in ()).throw(AssertionError("api key resolved")),
    )

    result = news_fetcher.fetch_news("TSLA", "user-1")

    assert result == cached
    assert calls == {"ticker": "TSLA", "ttl_override": 300}


def test_fetch_news_returns_empty_and_records_health_when_key_missing(monkeypatch):
    health = []
    monkeypatch.setattr(news_fetcher, "get_news_cache", lambda ticker, ttl_override=None: None)
    monkeypatch.setattr(news_fetcher, "resolve_api_key", lambda user_id: (_ for _ in ()).throw(RuntimeError("missing key")))
    monkeypatch.setattr(news_fetcher, "record_source_health", lambda source_id, status, reason="": health.append((source_id, status, reason)))

    result = news_fetcher.fetch_news("TSLA", "user-1")

    assert result == []
    assert health == [("finnhub", "unavailable", "missing key")]


def test_fetch_news_saves_cache_and_records_ok(monkeypatch):
    saved = []
    health = []

    class Client:
        def __init__(self, api_key):
            self.api_key = api_key

        def company_news(self, symbol, _from=None, to=None):
            return [{"headline": f"{symbol} news"}]

    monkeypatch.setattr(news_fetcher, "get_news_cache", lambda ticker, ttl_override=None: None)
    monkeypatch.setattr(news_fetcher, "resolve_api_key", lambda user_id: "key")
    monkeypatch.setattr(news_fetcher.finnhub, "Client", Client)
    monkeypatch.setattr(news_fetcher, "save_news_cache", lambda ticker, articles: saved.append((ticker, articles)))
    monkeypatch.setattr(news_fetcher, "record_source_health", lambda source_id, status, reason="": health.append((source_id, status, reason)))

    result = news_fetcher.fetch_news("2330.TW", "user-1")

    assert result == [{"headline": "2330 news"}]
    assert saved == [("2330.TW", result)]
    assert health == [("finnhub", "ok", "")]
