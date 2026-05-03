from datetime import datetime
from zoneinfo import ZoneInfo

from src.core.market_calendar import (
    cache_ttl_seconds,
    is_market_open,
    market_for_ticker,
    seconds_until_next_market_open,
)


def test_market_for_ticker_detects_taiwan_suffixes():
    assert market_for_ticker("2330.TW") == "TW"
    assert market_for_ticker("6488.TWO") == "TW"
    assert market_for_ticker("TSLA") == "US"


def test_taiwan_market_open_session():
    now = datetime(2026, 5, 1, 10, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert is_market_open("2330.TW", now)
    assert cache_ttl_seconds("2330.TW", "quote", now) == 60
    assert cache_ttl_seconds("2330.TW", "intraday", now) == 60
    assert cache_ttl_seconds("2330.TW", "daily", now) == 6 * 3600


def test_taiwan_daily_cache_extends_after_close():
    now = datetime(2026, 5, 1, 16, 0, tzinfo=ZoneInfo("Asia/Taipei"))

    assert not is_market_open("2330.TW", now)
    assert cache_ttl_seconds("2330.TW", "daily", now) == 24 * 3600


def test_quote_cache_after_close_keeps_until_next_session():
    now = datetime(2026, 5, 1, 16, 0, tzinfo=ZoneInfo("Asia/Taipei"))

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
