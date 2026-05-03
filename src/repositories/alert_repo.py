from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Literal

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "alerts.db"

AlertDirection = Literal["above", "below"]


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL,
            ticker       TEXT NOT NULL,
            type         TEXT NOT NULL,
            direction    TEXT NOT NULL,
            threshold    REAL NOT NULL,
            strategy_id  TEXT,
            enabled      INTEGER NOT NULL DEFAULT 1,
            triggered_at REAL,
            expires_at   REAL,
            created_at   REAL NOT NULL,
            updated_at   REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_events (
            id           TEXT PRIMARY KEY,
            alert_id     TEXT NOT NULL,
            user_id      TEXT NOT NULL,
            ticker       TEXT NOT NULL,
            event_type   TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            delivered_at REAL,
            created_at   REAL NOT NULL,
            FOREIGN KEY(alert_id) REFERENCES alerts(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id)")
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_alerts_active
        ON alerts(enabled, triggered_at, expires_at)
    """)
    conn.commit()
    return conn


def create_price_alert(
    user_id: str,
    ticker: str,
    direction: AlertDirection,
    threshold: float,
    *,
    expires_at: float | None = None,
    db_path: Path = _DEFAULT_DB,
) -> dict[str, Any]:
    if direction not in {"above", "below"}:
        raise ValueError("direction must be 'above' or 'below'")
    now = time.time()
    alert = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "ticker": ticker.strip().upper(),
        "type": "price",
        "direction": direction,
        "threshold": float(threshold),
        "strategy_id": None,
        "enabled": True,
        "triggered_at": None,
        "expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO alerts (
                id, user_id, ticker, type, direction, threshold, strategy_id,
                enabled, triggered_at, expires_at, created_at, updated_at
            )
            VALUES (:id, :user_id, :ticker, :type, :direction, :threshold, :strategy_id,
                    :enabled, :triggered_at, :expires_at, :created_at, :updated_at)
            """,
            {**alert, "enabled": 1},
        )
    return alert


def list_alerts(
    user_id: str,
    *,
    include_disabled: bool = True,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM alerts WHERE user_id = ?"
    params: list[Any] = [user_id]
    if not include_disabled:
        query += " AND enabled = 1"
    query += " ORDER BY created_at DESC"
    with _conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_alert(row) for row in rows]


def list_active_alerts(db_path: Path = _DEFAULT_DB) -> list[dict[str, Any]]:
    now = time.time()
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts
            WHERE enabled = 1
              AND triggered_at IS NULL
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at ASC
            """,
            (now,),
        ).fetchall()
    return [_row_to_alert(row) for row in rows]


def get_alert(alert_id: str, db_path: Path = _DEFAULT_DB) -> dict[str, Any] | None:
    with _conn(db_path) as conn:
        row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    return _row_to_alert(row) if row else None


def set_alert_enabled(
    alert_id: str,
    enabled: bool,
    *,
    db_path: Path = _DEFAULT_DB,
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE alerts SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, time.time(), alert_id),
        )


def delete_alert(alert_id: str, *, db_path: Path = _DEFAULT_DB) -> None:
    with _conn(db_path) as conn:
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))


def mark_triggered(
    alert_id: str,
    *,
    event_type: str,
    payload: dict[str, Any],
    delivered_at: float | None = None,
    db_path: Path = _DEFAULT_DB,
) -> None:
    now = time.time()
    alert = get_alert(alert_id, db_path=db_path)
    if alert is None:
        raise ValueError(f"Alert not found: {alert_id}")
    with _conn(db_path) as conn:
        conn.execute(
            "UPDATE alerts SET triggered_at = ?, updated_at = ? WHERE id = ?",
            (now, now, alert_id),
        )
        conn.execute(
            """
            INSERT INTO alert_events (
                id, alert_id, user_id, ticker, event_type, payload_json,
                delivered_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                alert_id,
                alert["user_id"],
                alert["ticker"],
                event_type,
                json.dumps(payload, ensure_ascii=False),
                delivered_at,
                now,
            ),
        )


def list_events(
    user_id: str,
    *,
    limit: int = 50,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM alert_events
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, int(limit)),
        ).fetchall()
    return [_row_to_event(row) for row in rows]


def alert_is_triggered(alert: dict[str, Any], current_price: float) -> bool:
    if alert["direction"] == "above":
        return current_price >= float(alert["threshold"])
    if alert["direction"] == "below":
        return current_price <= float(alert["threshold"])
    return False


def _row_to_alert(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["enabled"] = bool(data["enabled"])
    return data


def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["payload"] = json.loads(data.pop("payload_json"))
    return data
