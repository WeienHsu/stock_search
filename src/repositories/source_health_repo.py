from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "source_health.db"


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS source_health (
            source_id       TEXT PRIMARY KEY,
            last_success_at  REAL,
            last_error       TEXT,
            last_status      TEXT NOT NULL,
            updated_at       REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def record_source_health(
    source_id: str,
    status: str,
    *,
    reason: str = "",
    last_success_at: float | None = None,
    db_path: Path = _DEFAULT_DB,
) -> dict[str, Any]:
    existing = get_source_health(source_id, db_path=db_path)
    now = time.time()
    if status == "ok":
        last_success_at = now
        last_error = ""
    else:
        last_success_at = last_success_at if last_success_at is not None else existing.get("last_success_at")
        last_error = reason or existing.get("last_error") or ""
    row = {
        "source_id": source_id,
        "last_success_at": last_success_at,
        "last_error": last_error,
        "last_status": status,
        "updated_at": now,
    }
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO source_health (
                source_id, last_success_at, last_error, last_status, updated_at
            )
            VALUES (:source_id, :last_success_at, :last_error, :last_status, :updated_at)
            """,
            row,
        )
    return get_source_health(source_id, db_path=db_path)


def get_source_health(source_id: str, *, db_path: Path = _DEFAULT_DB) -> dict[str, Any]:
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM source_health WHERE source_id = ?",
            (source_id,),
        ).fetchone()
    if not row:
        return {
            "source_id": source_id,
            "last_success_at": None,
            "last_error": "",
            "last_status": "unknown",
            "updated_at": None,
        }
    return dict(row)


def list_source_health(*, db_path: Path = _DEFAULT_DB) -> list[dict[str, Any]]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM source_health ORDER BY source_id ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def format_health_summary(health: dict[str, Any]) -> str:
    status = str(health.get("last_status") or "unknown")
    last_success_at = health.get("last_success_at")
    last_error = str(health.get("last_error") or "")
    if last_success_at:
        ts = datetime.fromtimestamp(float(last_success_at)).strftime("%Y-%m-%d %H:%M")
    else:
        ts = "—"
    if status == "ok":
        return f"最後成功：{ts}"
    if status == "unsupported":
        return last_error or "不支援"
    if status == "unavailable":
        return f"最後成功：{ts}；最近錯誤：{last_error or '—'}"
    return last_error or "尚無紀錄"


def export_source_health_json(*, db_path: Path = _DEFAULT_DB) -> str:
    return json.dumps(list_source_health(db_path=db_path), ensure_ascii=False, indent=2)
