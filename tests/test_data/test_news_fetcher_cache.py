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
