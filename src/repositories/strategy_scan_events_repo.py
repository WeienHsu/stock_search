from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "strategy_scan_events.db"


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_scan_events (
            user_id      TEXT NOT NULL,
            ticker       TEXT NOT NULL,
            strategy_id  TEXT NOT NULL,
            signal_type  TEXT NOT NULL,
            date         TEXT NOT NULL,
            status       TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at   REAL NOT NULL,
            updated_at   REAL NOT NULL,
            PRIMARY KEY (user_id, ticker, strategy_id, date, signal_type)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_strategy_scan_events_user_date "
        "ON strategy_scan_events(user_id, date)"
    )
    conn.commit()
    return conn


def save_scan_event(
    user_id: str,
    ticker: str,
    strategy_id: str,
    signal_type: str,
    date: str,
    status: str,
    payload: dict[str, Any] | None = None,
    *,
    db_path: Path = _DEFAULT_DB,
) -> None:
    normalized_status = str(status).strip().lower()
    if normalized_status not in {"triggered", "no_signal", "error"}:
        raise ValueError("status must be triggered, no_signal, or error")
    row = {
        "user_id": user_id,
        "ticker": ticker.strip().upper(),
        "strategy_id": strategy_id.strip(),
        "signal_type": signal_type.strip().lower(),
        "date": str(date)[:10],
        "status": normalized_status,
        "payload_json": json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
        "now": time.time(),
    }
    if not all(row[key] for key in ("user_id", "ticker", "strategy_id", "signal_type", "date")):
        raise ValueError("user_id, ticker, strategy_id, signal_type, and date are required")
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO strategy_scan_events (
                user_id, ticker, strategy_id, signal_type, date, status,
                payload_json, created_at, updated_at
            )
            VALUES (
                :user_id, :ticker, :strategy_id, :signal_type, :date, :status,
                :payload_json,
                COALESCE(
                    (
                        SELECT created_at FROM strategy_scan_events
                        WHERE user_id = :user_id
                          AND ticker = :ticker
                          AND strategy_id = :strategy_id
                          AND signal_type = :signal_type
                          AND date = :date
                    ),
                    :now
                ),
                :now
            )
            """,
            row,
        )


def list_scan_events(
    user_id: str,
    *,
    since_date: str | None = None,
    ticker: str | None = None,
    strategy_id: str | None = None,
    status: str | None = None,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    clauses = ["user_id = ?"]
    params: list[Any] = [user_id]
    if since_date:
        clauses.append("date >= ?")
        params.append(str(since_date)[:10])
    if ticker:
        clauses.append("ticker = ?")
        params.append(ticker.strip().upper())
    if strategy_id:
        clauses.append("strategy_id = ?")
        params.append(strategy_id.strip())
    if status:
        clauses.append("status = ?")
        params.append(status.strip().lower())

    with _conn(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM strategy_scan_events
            WHERE {' AND '.join(clauses)}
            ORDER BY date DESC, ticker ASC, signal_type ASC
            """,
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    try:
        item["payload"] = json.loads(str(item.get("payload_json") or "{}"))
    except json.JSONDecodeError:
        item["payload"] = {}
    return item
