from __future__ import annotations

from datetime import datetime, time

from src.core.market_calendar import TAIWAN_TZ

_TW_OPEN = time(9, 0)
_TW_CLOSE = time(13, 30)


def get_ttl(base_ttl: int, market_hours_ttl: int = 60, now: datetime | None = None) -> int:
    """
    Cap a cache TTL during regular Taiwan market hours.

    Streamlit evaluates decorator TTLs at import time, so this helper is a small
    policy function rather than a per-call invalidation mechanism.
    """
    if base_ttl <= 0:
        raise ValueError("base_ttl must be positive")
    if market_hours_ttl <= 0:
        raise ValueError("market_hours_ttl must be positive")
    if is_taiwan_market_hours(now):
        return min(base_ttl, market_hours_ttl)
    return base_ttl


def is_taiwan_market_hours(now: datetime | None = None) -> bool:
    current = _taipei_now(now)
    if current.weekday() >= 5:
        return False
    return _TW_OPEN <= current.time() <= _TW_CLOSE


def _taipei_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(TAIWAN_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=TAIWAN_TZ)
    return now.astimezone(TAIWAN_TZ)
