from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable

_log = logging.getLogger(__name__)

# ── Event name constants ──────────────────────────────────────────────────────

PRICE_TICK = "price.tick"
SCHEDULE_DAILY = "schedule.daily"
SCHEDULE_WEEKLY = "schedule.weekly"
SCHEDULE_CHIP_SNAPSHOT = "schedule.chip_snapshot"
SCHEDULE_MARKET_OPEN = "schedule.market_open"
SCHEDULE_MARKET_CLOSE = "schedule.market_close"
WATCHLIST_ADDED = "watchlist.added"
ALERT_TRIGGERED = "alert.triggered"

# ── Event dataclass ───────────────────────────────────────────────────────────

Handler = Callable[["Event"], None]


@dataclass
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── EventBus ──────────────────────────────────────────────────────────────────


class EventBus:
    """In-process, thread-safe pub/sub event bus.

    Handlers are called synchronously in subscription order.
    A failing handler's exception is captured and returned; remaining
    handlers still execute.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = {}
        self._lock = Lock()

    def subscribe(self, event_name: str, handler: Handler) -> None:
        with self._lock:
            self._handlers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: Handler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_name, [])
            self._handlers[event_name] = [h for h in handlers if h is not handler]

    def emit(self, event: Event) -> list[Exception]:
        """Dispatch event to all subscribers.

        Returns list of exceptions raised by handlers (never re-raises).
        """
        with self._lock:
            handlers = list(self._handlers.get(event.name, []))
        errors: list[Exception] = []
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                _log.error(
                    "EventBus handler error [%s]: %s",
                    event.name,
                    exc,
                    exc_info=True,
                )
                errors.append(exc)
        return errors

    def subscriber_count(self, event_name: str) -> int:
        with self._lock:
            return len(self._handlers.get(event_name, []))

    def clear(self) -> None:
        """Remove all subscribers. Intended for test isolation."""
        with self._lock:
            self._handlers.clear()


# ── Module-level singleton + public API ──────────────────────────────────────

_bus = EventBus()


def subscribe(event_name: str, handler: Handler) -> None:
    _bus.subscribe(event_name, handler)


def unsubscribe(event_name: str, handler: Handler) -> None:
    _bus.unsubscribe(event_name, handler)


def emit(event: Event) -> list[Exception]:
    return _bus.emit(event)
