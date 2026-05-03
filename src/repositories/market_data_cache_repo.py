from __future__ import annotations

from typing import Any

from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="market_data")
_TTL = 3600


def get_market_cache(key: str, ttl_override: int | None = None) -> Any | None:
    ttl_seconds = ttl_override if ttl_override is not None else _TTL
    if not _backend.is_fresh("global", key, ttl_seconds=ttl_seconds):
        return None
    return _backend.get("global", key)


def save_market_cache(key: str, value: Any) -> None:
    _backend.save("global", key, value)
