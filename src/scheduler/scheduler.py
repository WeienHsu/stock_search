from __future__ import annotations

import logging
import os

from src.scheduler import events as _events

_log = logging.getLogger(__name__)
_scheduler = None
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
    from src.scheduler.jobs.weekly_digest import run_weekly_digest

    _events.subscribe(_events.PRICE_TICK, lambda e: run_price_alerts())
    _events.subscribe(_events.SCHEDULE_DAILY, lambda e: run_daily_scan())
    _events.subscribe(_events.SCHEDULE_CHIP_SNAPSHOT, lambda e: run_chip_daily_snapshot())
    _events.subscribe(_events.SCHEDULE_WEEKLY, lambda e: run_weekly_digest())

    from src.scheduler.jobs.daily_digest import register_event_handlers as _register_digest
    _register_digest()

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
    scheduler.add_job(
        lambda: _emit_event(_events.SCHEDULE_WEEKLY),
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_digest",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # ── New market lifecycle events (for Phase 10 daily digest and beyond) ──
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


def start_background_scheduler():
    global _scheduler
    if os.getenv("ENABLE_STREAMLIT_SCHEDULER", "0") != "1":
        return None
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = build_scheduler(blocking=False)
    _scheduler.start()
    return _scheduler
