from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DRY_RUN_PATH = ".cache/dry_run_notifications.jsonl"


def is_dry_run_enabled() -> bool:
    return os.getenv("NOTIFICATION_DRY_RUN", "0").strip().lower() in {"1", "true", "yes"}


def append_notification(payload: dict[str, Any], path: str | None = None) -> None:
    target = Path(path or os.getenv("NOTIFICATION_DRY_RUN_PATH") or DEFAULT_DRY_RUN_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
