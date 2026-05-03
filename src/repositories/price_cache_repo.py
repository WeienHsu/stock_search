import pandas as pd
from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="prices")
_TTL = 6 * 3600  # 6 hours


def get_price_cache(key: str, ttl_override: int | None = None) -> pd.DataFrame | None:
    ttl_seconds = ttl_override if ttl_override is not None else _TTL
    if not _backend.is_fresh("global", key, ttl_seconds=ttl_seconds):
        return None
    return _backend.get("global", key)


def save_price_cache(key: str, df: pd.DataFrame) -> None:
    _backend.save("global", key, df)
