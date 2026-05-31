from datetime import datetime
from zoneinfo import ZoneInfo

import src.core.market_calendar as market_calendar
from src.core.market_calendar import (
    cache_ttl_seconds,
    is_market_open,
    is_trading_day,
    last_market_close_dt,
    market_for_ticker,
    seconds_until_next_market_open,
)


def test_market_for_ticker_detects_taiwan_suffixes():
    assert market_for_ticker("2330.TW") == "TW"
    assert market_for_ticker("6488.TWO") == "TW"
    assert market_for_ticker("TSLA") == "US"


def test_taiwan_market_open_session():
    now = datetime(2026, 5, 4, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert is_market_open("2330.TW", now)
    assert cache_ttl_seconds("2330.TW", "quote", now) == 60
    assert cache_ttl_seconds("2330.TW", "intraday", now) == 60
    assert cache_ttl_seconds("2330.TW", "daily", now) == 6 * 3600


def test_is_trading_day_uses_exchange_calendar(monkeypatch):
    class FakeCalendar:
        def is_session(self, session):
            return str(session.date()) != "2026-02-16"

    monkeypatch.setattr(market_calendar, "_exchange_calendar", lambda market: FakeCalendar())

    assert not is_trading_day("2330.TW", datetime(2026, 2, 16, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")))
    assert is_trading_day("2330.TW", datetime(2026, 2, 17, 10, 0, tzinfo=ZoneInfo("Asia/Taipei")))


def test_is_trading_day_degrades_to_weekday_when_calendar_unavailable(monkeypatch):
    monkeypatch.setattr(market_calendar, "_exchange_calendar", lambda market: None)

    assert is_trading_day("TSLA", datetime(2026, 11, 26, 10, 0, tzinfo=ZoneInfo("America/New_York")))
    assert not is_trading_day("TSLA", datetime(2026, 11, 28, 10, 0, tzinfo=ZoneInfo("America/New_York")))


def test_taiwan_daily_cache_post_close_equals_elapsed_since_close():
    # 16:00 is 2.5h after TW close (13:30) → TTL == elapsed == 9000s
    # A cache written before 13:30 has age > 9000s → stale (forces refetch).
    now = datetime(2026, 5, 4, 16, 0, tzinfo=ZoneInfo("Asia/Taipei"))
    last_close = last_market_close_dt("2330.TW", now)
    elapsed = int((now - last_close).total_seconds())

    assert not is_market_open("2330.TW", now)
    assert cache_ttl_seconds("2330.TW", "daily", now) == elapsed  # 9000s

    # A cache written BEFORE close (e.g., at 11:00) should be considered stale.
    pre_close_cache_age = int((now - datetime(2026, 5, 4, 11, 0, tzinfo=ZoneInfo("Asia/Taipei"))).total_seconds())
    assert pre_close_cache_age > elapsed, "pre-close cache must be older than TTL → stale"


def test_quote_cache_after_close_keeps_until_next_session():
    now = datetime(2026, 5, 8, 16, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert seconds_until_next_market_open("2330.TW", now) == 65 * 3600
    assert cache_ttl_seconds("2330.TW", "quote", now) == 65 * 3600


def test_us_market_open_session_converts_timezone():
    taipei_now = datetime(2026, 5, 2, 3, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert is_market_open("TSLA", taipei_now)
    assert cache_ttl_seconds("TSLA", "quote", taipei_now) == 60


def test_static_granularity_ttls():
    now = datetime(2026, 5, 1, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert cache_ttl_seconds("TSLA", "news", now) == 5 * 60
    assert cache_ttl_seconds("TSLA", "company_profile", now) == 7 * 24 * 3600
