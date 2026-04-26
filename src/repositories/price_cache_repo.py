import pandas as pd
from src.repositories._backends.pickle_backend import PickleBackend

_backend = PickleBackend(subdir="prices")
_TTL = 6 * 3600  # 6 hours


def get_price_cache(ticker: str) -> pd.DataFrame | None:
    if not _backend.is_fresh("global", ticker, ttl_seconds=_TTL):
        return None
    return _backend.get("global", ticker)


def save_price_cache(ticker: str, df: pd.DataFrame) -> None:
    _backend.save("global", ticker, df)
