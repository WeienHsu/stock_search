from __future__ import annotations

from typing import Any

from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="chip_data")
_DAY = 24 * 3600


def get_chip_cache(key: str, ttl_override: int | None = None) -> Any | None:
    ttl_seconds = ttl_override if ttl_override is not None else _DAY
    if not _backend.is_fresh("global", key, ttl_seconds=ttl_seconds):
        return None
    return _backend.get("global", key)


def save_chip_cache(key: str, value: Any) -> None:
    _backend.save("global", key, value)


def clear_chip_cache(user_id: str = "global") -> int:
    return _backend.clear_user(user_id)
