from datetime import datetime

import pytest

from src.core.market_calendar import TAIWAN_TZ
from src.data.dynamic_ttl import get_ttl, is_taiwan_market_hours


def test_get_ttl_caps_base_ttl_during_taiwan_market_hours():
    now = datetime(2026, 5, 8, 10, 0, tzinfo=TAIWAN_TZ)

    assert get_ttl(600, market_hours_ttl=60, now=now) == 60


def test_get_ttl_keeps_base_ttl_after_hours():
    now = datetime(2026, 5, 8, 15, 0, tzinfo=TAIWAN_TZ)

    assert get_ttl(600, market_hours_ttl=60, now=now) == 600


def test_get_ttl_does_not_lengthen_short_base_ttl():
    now = datetime(2026, 5, 8, 10, 0, tzinfo=TAIWAN_TZ)

    assert get_ttl(30, market_hours_ttl=60, now=now) == 30


def test_weekend_is_not_market_hours():
    saturday = datetime(2026, 5, 9, 10, 0, tzinfo=TAIWAN_TZ)

    assert is_taiwan_market_hours(saturday) is False
    assert get_ttl(600, market_hours_ttl=60, now=saturday) == 600


def test_get_ttl_rejects_non_positive_values():
    with pytest.raises(ValueError):
        get_ttl(0)
    with pytest.raises(ValueError):
        get_ttl(600, market_hours_ttl=0)
