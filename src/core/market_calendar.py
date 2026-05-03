from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

Market = Literal["TW", "US"]
Granularity = Literal["quote", "intraday", "daily", "company_profile", "news"]

TAIWAN_TZ = ZoneInfo("Asia/Taipei")
US_TZ = ZoneInfo("America/New_York")

_TW_OPEN = time(9, 0)
_TW_CLOSE = time(13, 30)
_US_OPEN = time(9, 30)
_US_CLOSE = time(16, 0)

_MINUTE = 60
_HOUR = 3600
_DAY = 24 * _HOUR


def market_for_ticker(ticker: str) -> Market:
    """Infer the primary market from the ticker format."""
    normalized = ticker.upper()
    if normalized.endswith((".TW", ".TWO")):
        return "TW"
    return "US"


def is_market_open(ticker: str, now: datetime | None = None) -> bool:
    local_now = _local_now(ticker, now)
    if local_now.weekday() >= 5:
        return False

    open_time, close_time = _session_times(ticker)
    current_time = local_now.time()
    return open_time <= current_time <= close_time


def seconds_until_next_market_open(ticker: str, now: datetime | None = None) -> int:
    local_now = _local_now(ticker, now)
    open_time, close_time = _session_times(ticker)

    candidate_date = local_now.date()
    if local_now.weekday() >= 5 or local_now.time() > close_time:
        candidate_date += timedelta(days=1)

    while candidate_date.weekday() >= 5:
        candidate_date += timedelta(days=1)

    candidate = datetime.combine(candidate_date, open_time, tzinfo=local_now.tzinfo)
    if candidate <= local_now:
        candidate += timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

    return max(1, int((candidate - local_now).total_seconds()))


def cache_ttl_seconds(
    ticker: str,
    granularity: Granularity = "daily",
    now: datetime | None = None,
) -> int:
    """
    Return the cache TTL for the requested data granularity.

    Holiday calendars are intentionally not modeled in P0; weekends and regular
    sessions cover the dynamic TTL behavior without adding external dependencies.
    """
    if granularity in {"quote", "intraday"}:
        if is_market_open(ticker, now):
            return _MINUTE
        return seconds_until_next_market_open(ticker, now)

    if granularity == "daily":
        return 6 * _HOUR if is_market_open(ticker, now) else _DAY

    if granularity == "company_profile":
        return 7 * _DAY

    if granularity == "news":
        return 5 * _MINUTE

    raise ValueError(f"Unsupported cache granularity: {granularity}")


def _local_now(ticker: str, now: datetime | None = None) -> datetime:
    tz = TAIWAN_TZ if market_for_ticker(ticker) == "TW" else US_TZ
    if now is None:
        return datetime.now(tz)
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)


def _session_times(ticker: str) -> tuple[time, time]:
    if market_for_ticker(ticker) == "TW":
        return _TW_OPEN, _TW_CLOSE
    return _US_OPEN, _US_CLOSE
