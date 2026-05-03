from typing import Any
from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="news")
_TTL = 3600  # 1 hour


def get_news_cache(ticker: str, ttl_override: int | None = None) -> list[dict] | None:
    ttl_seconds = ttl_override if ttl_override is not None else _TTL
    if not _backend.is_fresh("global", ticker, ttl_seconds=ttl_seconds):
        return None
    return _backend.get("global", ticker)


def save_news_cache(ticker: str, articles: list[dict[str, Any]]) -> None:
    _backend.save("global", ticker, articles)
