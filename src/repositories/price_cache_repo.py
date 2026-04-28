import pandas as pd
from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="prices")
_TTL = 6 * 3600  # 6 hours


def get_price_cache(key: str) -> pd.DataFrame | None:
    if not _backend.is_fresh("global", key, ttl_seconds=_TTL):
        return None
    return _backend.get("global", key)


def save_price_cache(key: str, df: pd.DataFrame) -> None:
    _backend.save("global", key, df)
