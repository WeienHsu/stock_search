from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "chip_snapshots.db"


def _conn(db_path: Path = _DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chip_snapshots (
            ticker                    TEXT NOT NULL,
            date                      TEXT NOT NULL,
            institutional_foreign     REAL NOT NULL DEFAULT 0,
            institutional_trust       REAL NOT NULL DEFAULT 0,
            institutional_dealer      REAL NOT NULL DEFAULT 0,
            margin_balance            REAL NOT NULL DEFAULT 0,
            short_balance             REAL NOT NULL DEFAULT 0,
            qfiis_pct                 REAL,
            source                    TEXT NOT NULL DEFAULT '',
            created_at                REAL NOT NULL DEFAULT (strftime('%s','now')),
            updated_at                REAL NOT NULL DEFAULT (strftime('%s','now')),
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.commit()
    return conn


def save_chip_snapshot(snapshot: dict[str, Any], *, db_path: Path = _DEFAULT_DB) -> None:
    payload = {
        "ticker": str(snapshot.get("ticker", "")).strip().upper(),
        "date": str(snapshot.get("date", "")).strip(),
        "institutional_foreign": float(snapshot.get("institutional_foreign", 0) or 0),
        "institutional_trust": float(snapshot.get("institutional_trust", 0) or 0),
        "institutional_dealer": float(snapshot.get("institutional_dealer", 0) or 0),
        "margin_balance": float(snapshot.get("margin_balance", 0) or 0),
        "short_balance": float(snapshot.get("short_balance", 0) or 0),
        "qfiis_pct": snapshot.get("qfiis_pct"),
        "source": _normalize_source(snapshot.get("source", "")),
    }
    if not payload["ticker"] or not payload["date"]:
        raise ValueError("snapshot must include ticker and date")
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chip_snapshots (
                ticker, date, institutional_foreign, institutional_trust,
                institutional_dealer, margin_balance, short_balance, qfiis_pct,
                source, created_at, updated_at
            )
            VALUES (
                :ticker, :date, :institutional_foreign, :institutional_trust,
                :institutional_dealer, :margin_balance, :short_balance, :qfiis_pct,
                :source, COALESCE(
                    (SELECT created_at FROM chip_snapshots WHERE ticker = :ticker AND date = :date),
                    strftime('%s','now')
                ), strftime('%s','now')
            )
            """,
            payload,
        )


def get_latest_snapshot(ticker: str, *, db_path: Path = _DEFAULT_DB) -> dict[str, Any] | None:
    with _conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM chip_snapshots
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (ticker.strip().upper(),),
        ).fetchone()
    return dict(row) if row else None


def list_recent_snapshots(
    ticker: str,
    *,
    limit: int = 20,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM chip_snapshots
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (ticker.strip().upper(), int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]


def list_snapshot_tickers(*, db_path: Path = _DEFAULT_DB) -> list[str]:
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM chip_snapshots ORDER BY ticker ASC"
        ).fetchall()
    return [str(row[0]) for row in rows]


def _normalize_source(value: Any) -> str:
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value or "")
