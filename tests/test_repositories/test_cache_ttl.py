import pandas as pd

from src.repositories import news_cache_repo, price_cache_repo


class FakeBackend:
    def __init__(self):
        self.ttl_seconds = None
        self.saved = {}
        self.fresh = True

    def is_fresh(self, user_id, key, ttl_seconds=21600):
        self.ttl_seconds = ttl_seconds
        return self.fresh

    def get(self, user_id, key):
        return self.saved.get((user_id, key))

    def save(self, user_id, key, value):
        self.saved[(user_id, key)] = value


def test_price_cache_uses_ttl_override(monkeypatch):
    backend = FakeBackend()
    df = pd.DataFrame({"close": [100]})
    backend.saved[("global", "TSLA_1y")] = df
    monkeypatch.setattr(price_cache_repo, "_backend", backend)

    result = price_cache_repo.get_price_cache("TSLA_1y", ttl_override=60)

    assert result.equals(df)
    assert backend.ttl_seconds == 60


def test_price_cache_falls_back_to_default_ttl(monkeypatch):
    backend = FakeBackend()
    backend.saved[("global", "TSLA_1y")] = pd.DataFrame({"close": [100]})
    monkeypatch.setattr(price_cache_repo, "_backend", backend)

    price_cache_repo.get_price_cache("TSLA_1y")

    assert backend.ttl_seconds == 6 * 3600


def test_news_cache_uses_ttl_override(monkeypatch):
    backend = FakeBackend()
    articles = [{"headline": "test"}]
    backend.saved[("global", "TSLA")] = articles
    monkeypatch.setattr(news_cache_repo, "_backend", backend)

    result = news_cache_repo.get_news_cache("TSLA", ttl_override=300)

    assert result == articles
    assert backend.ttl_seconds == 300
