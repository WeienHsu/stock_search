from typing import Any
from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="news")
_TTL = 3600  # 1 hour


def get_news_cache(ticker: str) -> list[dict] | None:
    if not _backend.is_fresh("global", ticker, ttl_seconds=_TTL):
        return None
    return _backend.get("global", ticker)


def save_news_cache(ticker: str, articles: list[dict[str, Any]]) -> None:
    _backend.save("global", ticker, articles)
