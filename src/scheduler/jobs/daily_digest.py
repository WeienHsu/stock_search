from __future__ import annotations

import json
from datetime import date
from typing import Any

from src.ai.digest_generator import run_digest
from src.auth.auth_manager import list_users
from src.notifications import send_notification
from src.repositories import user_prefs_repo
from src.repositories.scheduler_run_repo import finish_run, start_run
from src.scheduler import events as _events

JOB_NAME = "daily_digest"
_DIGEST_NS = "digest_settings"
_CACHE_NS = "digest_cache"

# Digest type constants
PRE_MARKET = "pre_market"
POST_MARKET = "post_market"


def run_daily_digest(user_id: str, digest_type: str) -> dict[str, Any]:
    """Generate and send a daily digest for one user.

    Returns a result dict describing what happened (skipped / delivered / error).
    """
    prefs = user_prefs_repo.get(user_id, _DIGEST_NS)
    if not prefs.get("enabled"):
        return {"skipped": True, "reason": "disabled"}

    enabled_types = _enabled_types(prefs)
    if digest_type not in enabled_types:
        return {"skipped": True, "reason": f"{digest_type}_disabled"}

    # Same-day dedup: avoid re-sending if already delivered today
    cache = user_prefs_repo.get(user_id, _CACHE_NS)
    today = str(date.today())
    if cache.get(digest_type, {}).get("date") == today:
        return {"skipped": True, "reason": "already_sent_today"}

    content, used_ai = run_digest(user_id, digest_type)
    subject = "盤前摘要" if digest_type == PRE_MARKET else "盤後摘要"
    results = send_notification(
        user_id,
        subject,
        content,
        severity="info",
        event_type="daily_digest",
    )

    # Update same-day cache
    cache[digest_type] = {"date": today}
    user_prefs_repo.set(user_id, _CACHE_NS, cache)

    delivered = any(r.success for r in results)
    return {
        "skipped": False,
        "delivered": delivered,
        "used_ai": used_ai,
        "channels": [r.channel for r in results],
    }


def _run_all_users(digest_type: str) -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    users_sent = 0
    users_skipped = 0
    try:
        for user in list_users():
            result = run_daily_digest(user["user_id"], digest_type)
            if result.get("skipped"):
                users_skipped += 1
            else:
                users_sent += 1
        finish_run(run_id, "success")
        return {"users_sent": users_sent, "users_skipped": users_skipped}
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise


def register_event_handlers() -> None:
    """Subscribe to market-lifecycle events. Called once from scheduler._register_job_handlers()."""
    _events.subscribe(_events.SCHEDULE_MARKET_OPEN, lambda e: _run_all_users(PRE_MARKET))
    _events.subscribe(_events.SCHEDULE_MARKET_CLOSE, lambda e: _run_all_users(POST_MARKET))


def _enabled_types(prefs: dict[str, Any]) -> set[str]:
    enabled: set[str] = set()
    if prefs.get("pre_market", True):
        enabled.add(PRE_MARKET)
    if prefs.get("post_market", False):
        enabled.add(POST_MARKET)
    return enabled


if __name__ == "__main__":
    import sys
    uid = sys.argv[1] if len(sys.argv) > 1 else "local"
    dtype = sys.argv[2] if len(sys.argv) > 2 else PRE_MARKET
    print(json.dumps(run_daily_digest(uid, dtype), ensure_ascii=False, default=str))
