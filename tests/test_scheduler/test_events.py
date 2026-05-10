from __future__ import annotations

import threading

from src.scheduler.events import (
    ALERT_TRIGGERED,
    PRICE_TICK,
    SCHEDULE_CHIP_SNAPSHOT,
    SCHEDULE_DAILY,
    SCHEDULE_MARKET_CLOSE,
    SCHEDULE_MARKET_OPEN,
    SCHEDULE_WEEKLY,
    WATCHLIST_ADDED,
    Event,
    EventBus,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _bus() -> EventBus:
    """Return a fresh EventBus for each test."""
    return EventBus()


# ── Constants ─────────────────────────────────────────────────────────────────


def test_all_event_name_constants_are_strings():
    constants = [
        PRICE_TICK,
        SCHEDULE_DAILY,
        SCHEDULE_WEEKLY,
        SCHEDULE_CHIP_SNAPSHOT,
        SCHEDULE_MARKET_OPEN,
        SCHEDULE_MARKET_CLOSE,
        WATCHLIST_ADDED,
        ALERT_TRIGGERED,
    ]
    assert all(isinstance(c, str) and c for c in constants)


# ── Event dataclass ───────────────────────────────────────────────────────────


def test_event_defaults_are_safe():
    e = Event(name=PRICE_TICK)
    assert e.name == PRICE_TICK
    assert e.payload == {}
    assert e.user_id == ""
    assert e.timestamp is not None


def test_event_carries_payload_and_user_id():
    e = Event(name=SCHEDULE_DAILY, payload={"source": "cron"}, user_id="local")
    assert e.payload["source"] == "cron"
    assert e.user_id == "local"


# ── subscribe / emit ──────────────────────────────────────────────────────────


def test_subscribe_and_emit_calls_handler():
    bus = _bus()
    received: list[Event] = []
    bus.subscribe(PRICE_TICK, received.append)

    bus.emit(Event(name=PRICE_TICK, payload={"price": 100.0}))

    assert len(received) == 1
    assert received[0].payload["price"] == 100.0


def test_multiple_handlers_all_called_in_order():
    bus = _bus()
    order: list[str] = []
    bus.subscribe(PRICE_TICK, lambda e: order.append("first"))
    bus.subscribe(PRICE_TICK, lambda e: order.append("second"))

    bus.emit(Event(name=PRICE_TICK))

    assert order == ["first", "second"]


def test_emit_unknown_event_returns_empty_errors():
    bus = _bus()
    errors = bus.emit(Event(name="totally.unknown"))
    assert errors == []


def test_handler_exception_is_captured_not_raised():
    bus = _bus()

    def _bad(e: Event) -> None:
        raise ValueError("boom")

    bus.subscribe(PRICE_TICK, _bad)
    errors = bus.emit(Event(name=PRICE_TICK))

    assert len(errors) == 1
    assert isinstance(errors[0], ValueError)


def test_handler_error_does_not_prevent_subsequent_handlers():
    bus = _bus()
    completed: list[str] = []

    bus.subscribe(PRICE_TICK, lambda e: (_ for _ in ()).throw(RuntimeError("first fails")))
    bus.subscribe(PRICE_TICK, lambda e: completed.append("second ran"))

    errors = bus.emit(Event(name=PRICE_TICK))

    assert len(errors) == 1
    assert completed == ["second ran"]


def test_different_event_names_are_independent():
    bus = _bus()
    price_calls: list[Event] = []
    daily_calls: list[Event] = []

    bus.subscribe(PRICE_TICK, price_calls.append)
    bus.subscribe(SCHEDULE_DAILY, daily_calls.append)

    bus.emit(Event(name=PRICE_TICK))

    assert len(price_calls) == 1
    assert len(daily_calls) == 0


# ── unsubscribe ───────────────────────────────────────────────────────────────


def test_unsubscribe_removes_specific_handler():
    bus = _bus()
    calls: list[str] = []
    handler_a = lambda e: calls.append("A")
    handler_b = lambda e: calls.append("B")

    bus.subscribe(PRICE_TICK, handler_a)
    bus.subscribe(PRICE_TICK, handler_b)
    bus.unsubscribe(PRICE_TICK, handler_a)

    bus.emit(Event(name=PRICE_TICK))

    assert calls == ["B"]


def test_unsubscribe_nonexistent_handler_is_safe():
    bus = _bus()
    bus.unsubscribe(PRICE_TICK, lambda e: None)  # must not raise


# ── subscriber_count ──────────────────────────────────────────────────────────


def test_subscriber_count_reflects_subscriptions():
    bus = _bus()
    assert bus.subscriber_count(PRICE_TICK) == 0

    bus.subscribe(PRICE_TICK, lambda e: None)
    bus.subscribe(PRICE_TICK, lambda e: None)

    assert bus.subscriber_count(PRICE_TICK) == 2


def test_subscriber_count_decreases_after_unsubscribe():
    bus = _bus()
    h = lambda e: None
    bus.subscribe(PRICE_TICK, h)
    bus.unsubscribe(PRICE_TICK, h)

    assert bus.subscriber_count(PRICE_TICK) == 0


# ── clear ─────────────────────────────────────────────────────────────────────


def test_clear_removes_all_subscribers():
    bus = _bus()
    calls: list[Event] = []
    bus.subscribe(PRICE_TICK, calls.append)
    bus.subscribe(SCHEDULE_DAILY, calls.append)

    bus.clear()
    bus.emit(Event(name=PRICE_TICK))
    bus.emit(Event(name=SCHEDULE_DAILY))

    assert calls == []


# ── thread safety ─────────────────────────────────────────────────────────────


def test_concurrent_emit_does_not_race():
    """Smoke test: 20 threads each emit 50 events; no exception raised."""
    bus = _bus()
    results: list[str] = []
    lock = threading.Lock()

    def _handler(e: Event) -> None:
        with lock:
            results.append(e.name)

    bus.subscribe(PRICE_TICK, _handler)

    threads = [
        threading.Thread(target=lambda: [bus.emit(Event(name=PRICE_TICK)) for _ in range(50)])
        for _ in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 20 * 50


# ── scheduler integration ─────────────────────────────────────────────────────


def test_register_job_handlers_subscribes_to_correct_events(monkeypatch):
    """Verify that _register_job_handlers wires jobs to the right event names."""
    import src.scheduler.scheduler as sched_mod

    # Use a fresh EventBus so we don't pollute the global singleton
    fresh_bus = EventBus()
    monkeypatch.setattr(sched_mod._events, "_bus", fresh_bus)
    monkeypatch.setattr(sched_mod, "_handlers_registered", False)

    # Stub out the heavy job functions
    monkeypatch.setattr("src.scheduler.jobs.price_alerts.run_price_alerts", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.daily_scan.run_daily_scan", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.chip_daily_snapshot.run_chip_daily_snapshot", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.weekly_digest.run_weekly_digest", lambda: None)

    sched_mod._register_job_handlers()

    assert fresh_bus.subscriber_count(PRICE_TICK) == 1
    assert fresh_bus.subscriber_count(SCHEDULE_DAILY) == 1
    assert fresh_bus.subscriber_count(SCHEDULE_CHIP_SNAPSHOT) == 1
    assert fresh_bus.subscriber_count(SCHEDULE_WEEKLY) == 1


def test_emit_schedule_event_calls_job_function(monkeypatch):
    """Verify that emitting a schedule event triggers the subscribed job."""
    import src.scheduler.scheduler as sched_mod

    fresh_bus = EventBus()
    monkeypatch.setattr(sched_mod._events, "_bus", fresh_bus)
    monkeypatch.setattr(sched_mod, "_handlers_registered", False)

    called: list[str] = []
    monkeypatch.setattr("src.scheduler.jobs.price_alerts.run_price_alerts", lambda: called.append("price_alerts"))
    monkeypatch.setattr("src.scheduler.jobs.daily_scan.run_daily_scan", lambda: called.append("daily_scan"))
    monkeypatch.setattr("src.scheduler.jobs.chip_daily_snapshot.run_chip_daily_snapshot", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.weekly_digest.run_weekly_digest", lambda: None)

    sched_mod._register_job_handlers()
    fresh_bus.emit(Event(name=PRICE_TICK))
    fresh_bus.emit(Event(name=SCHEDULE_DAILY))

    assert "price_alerts" in called
    assert "daily_scan" in called


def test_register_job_handlers_is_idempotent(monkeypatch):
    """Calling _register_job_handlers twice must not double-subscribe."""
    import src.scheduler.scheduler as sched_mod

    fresh_bus = EventBus()
    monkeypatch.setattr(sched_mod._events, "_bus", fresh_bus)
    monkeypatch.setattr(sched_mod, "_handlers_registered", False)

    monkeypatch.setattr("src.scheduler.jobs.price_alerts.run_price_alerts", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.daily_scan.run_daily_scan", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.chip_daily_snapshot.run_chip_daily_snapshot", lambda: None)
    monkeypatch.setattr("src.scheduler.jobs.weekly_digest.run_weekly_digest", lambda: None)

    sched_mod._register_job_handlers()
    sched_mod._register_job_handlers()  # second call must be a no-op

    assert fresh_bus.subscriber_count(PRICE_TICK) == 1
