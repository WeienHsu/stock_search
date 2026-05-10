from __future__ import annotations

from src.data.ticker_utils import normalize_ticker
from src.repositories.ticker_resolution_repo import get_resolved_ticker


def resolved_display_ticker(ticker: str) -> str:
    """Return the actual ticker suffix used for market-data lookup when known."""
    normalized = normalize_ticker(ticker)
    return get_resolved_ticker(normalized) or normalized


def should_sync_display_ticker(requested_ticker: str, display_ticker: str) -> bool:
    requested = normalize_ticker(requested_ticker)
    display = normalize_ticker(display_ticker)
    return bool(requested and display and requested != display)
