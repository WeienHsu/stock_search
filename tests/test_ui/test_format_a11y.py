from __future__ import annotations

from datetime import datetime, timezone

from src.ui.utils.format_a11y import format_taipei_datetime


def test_format_taipei_datetime_assumes_naive_datetime_is_taipei():
    value = datetime(2026, 5, 9, 14, 30)

    assert format_taipei_datetime(value) == "2026-05-09 14:30 (台北)"


def test_format_taipei_datetime_converts_aware_datetime_to_taipei():
    value = datetime(2026, 5, 9, 6, 30, tzinfo=timezone.utc)

    assert format_taipei_datetime(value) == "2026-05-09 14:30 (台北)"


def test_format_taipei_datetime_formats_epoch_seconds():
    value = datetime(2026, 5, 9, 6, 30, tzinfo=timezone.utc).timestamp()

    assert format_taipei_datetime(value) == "2026-05-09 14:30 (台北)"


def test_format_taipei_datetime_formats_twse_compact_time():
    result = format_taipei_datetime("133000")

    assert result.endswith("13:30 (台北)")


def test_format_taipei_datetime_can_omit_timezone_label():
    value = datetime(2026, 5, 9, 14, 30)

    assert format_taipei_datetime(value, with_tz_label=False) == "2026-05-09 14:30"


def test_format_taipei_datetime_handles_blank_values():
    assert format_taipei_datetime(None) == "—"
    assert format_taipei_datetime("") == "—"
