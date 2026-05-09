from __future__ import annotations

from datetime import date, datetime, time, timezone
from numbers import Real

from src.core.market_calendar import TAIWAN_TZ


def format_change(value: float, *, unit: str = "%", precision: int = 2) -> dict[str, str]:
    if value > 0:
        text = f"+{value:.{precision}f}{unit}"
        return {"text": text, "icon": "▲", "direction": "up", "aria_label": f"上漲 {text}"}
    if value < 0:
        text = f"−{abs(value):.{precision}f}{unit}"
        return {"text": text, "icon": "▼", "direction": "down", "aria_label": f"下跌 {text}"}
    text = f"0.{''.join(['0'] * precision)}{unit}"
    return {"text": text, "icon": "—", "direction": "flat", "aria_label": "無變化"}


def format_currency(value: float, *, precision: int = 2) -> str:
    if value < 0:
        return f"−{abs(value):,.{precision}f}"
    return f"{value:,.{precision}f}"


def format_percent(value: float, *, precision: int = 2) -> str:
    return format_change(value, unit="%", precision=precision)["text"]


def format_taipei_datetime(dt: datetime | date | time | str | Real | None, *, with_tz_label: bool = True) -> str:
    if dt is None:
        return "—"

    normalized = _to_taipei_datetime(dt)
    if normalized is None:
        return "—"

    text = normalized.strftime("%Y-%m-%d %H:%M")
    return f"{text} (台北)" if with_tz_label else text


def _to_taipei_datetime(value: datetime | date | time | str | Real) -> datetime | None:
    if isinstance(value, datetime):
        return _ensure_taipei(value)

    if isinstance(value, Real):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone(TAIWAN_TZ)

    if isinstance(value, date):
        return datetime.combine(value, time(), tzinfo=TAIWAN_TZ)

    if isinstance(value, time):
        today = datetime.now(TAIWAN_TZ).date()
        return datetime.combine(today, value, tzinfo=TAIWAN_TZ)

    text = str(value).strip()
    if not text:
        return None

    parsed = _parse_taipei_datetime_text(text)
    return _ensure_taipei(parsed) if parsed else None


def _parse_taipei_datetime_text(text: str) -> datetime | None:
    if text.isdigit() and len(text) in {4, 6}:
        compact_fmt = "%H%M%S" if len(text) == 6 else "%H%M"
        try:
            parsed_time = datetime.strptime(text, compact_fmt).time()
            return datetime.combine(datetime.now(TAIWAN_TZ).date(), parsed_time, tzinfo=TAIWAN_TZ)
        except ValueError:
            pass

    iso_text = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_text)
    except ValueError:
        pass

    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=TAIWAN_TZ)
        except ValueError:
            continue

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed_time = datetime.strptime(text, fmt).time()
            return datetime.combine(datetime.now(TAIWAN_TZ).date(), parsed_time, tzinfo=TAIWAN_TZ)
        except ValueError:
            continue

    return None


def _ensure_taipei(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=TAIWAN_TZ)
    return value.astimezone(TAIWAN_TZ)
