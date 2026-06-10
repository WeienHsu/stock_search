from __future__ import annotations

import logging

from src.scheduler import events as _events

_log = logging.getLogger(__name__)
_handlers_registered = False


def _emit_event(event_name: str) -> None:
    """Emit a schedule event and log any handler errors."""
    errors = _events.emit(_events.Event(name=event_name))
    for exc in errors:
        _log.error("Event handler error for %s: %s", event_name, exc)


def _register_job_handlers() -> None:
    """Subscribe existing job functions to their scheduler events (runs once)."""
    global _handlers_registered
    if _handlers_registered:
        return

    from src.scheduler.jobs.chip_daily_snapshot import run_chip_daily_snapshot
    from src.scheduler.jobs.daily_scan import run_daily_scan
    from src.scheduler.jobs.price_alerts import run_price_alerts

    _events.subscribe(_events.PRICE_TICK, lambda e: run_price_alerts())
    _events.subscribe(_events.SCHEDULE_DAILY, lambda e: run_daily_scan())
    _events.subscribe(_events.SCHEDULE_CHIP_SNAPSHOT, lambda e: run_chip_daily_snapshot())

    _handlers_registered = True


def build_scheduler(blocking: bool = False):
    _register_job_handlers()

    if blocking:
        from apscheduler.schedulers.blocking import BlockingScheduler
        scheduler = BlockingScheduler(timezone="Asia/Taipei")
    else:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone="Asia/Taipei")

    # ── Existing jobs: APScheduler emits events; EventBus dispatches to handlers ──
    scheduler.add_job(
        lambda: _emit_event(_events.PRICE_TICK),
        "interval",
        minutes=15,
        id="price_alerts",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_DAILY),
        "cron",
        hour=14,
        minute=10,
        id="daily_scan_tw",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_DAILY),
        "cron",
        hour=5,
        minute=10,
        id="daily_scan_us",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_CHIP_SNAPSHOT),
        "cron",
        day_of_week="mon-fri",
        hour=17,
        minute=30,
        id="chip_daily_snapshot",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    # ── Market lifecycle events ──
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_MARKET_OPEN),
        "cron",
        day_of_week="mon-fri",
        hour=8,
        minute=30,
        id="market_open",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_MARKET_CLOSE),
        "cron",
        day_of_week="mon-fri",
        hour=14,
        minute=30,
        id="market_close",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    return scheduler

