from __future__ import annotations

import os

from src.scheduler.jobs.chip_daily_snapshot import run_chip_daily_snapshot
from src.scheduler.jobs.daily_scan import run_daily_scan
from src.scheduler.jobs.price_alerts import run_price_alerts
from src.scheduler.jobs.weekly_digest import run_weekly_digest

_scheduler = None


def build_scheduler(blocking: bool = False):
    if blocking:
        from apscheduler.schedulers.blocking import BlockingScheduler

        scheduler = BlockingScheduler(timezone="Asia/Taipei")
    else:
        from apscheduler.schedulers.background import BackgroundScheduler

        scheduler = BackgroundScheduler(timezone="Asia/Taipei")

    scheduler.add_job(
        run_price_alerts,
        "interval",
        minutes=15,
        id="price_alerts",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_daily_scan,
        "cron",
        hour=14,
        minute=10,
        id="daily_scan_tw",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_daily_scan,
        "cron",
        hour=5,
        minute=10,
        id="daily_scan_us",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_chip_daily_snapshot,
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
        run_weekly_digest,
        "cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        id="weekly_digest",
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
