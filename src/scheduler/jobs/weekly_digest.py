from __future__ import annotations

from typing import Any

from src.repositories.scheduler_run_repo import finish_run, start_run

JOB_NAME = "weekly_digest"


def run_weekly_digest() -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    try:
        # P3 will attach the AI-written weekly digest body here. P1 only records
        # the scheduled run so worker wiring and auditability are in place.
        finish_run(run_id, "success")
        return {"status": "placeholder"}
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise
