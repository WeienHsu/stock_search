from pathlib import Path
from typing import Any
import time
from src.core.database import get_connection

_DEFAULT_DB = Path(__file__).parents[2] / "data" / "alerts.db"



def _conn(db_path: Path = _DEFAULT_DB) -> Any:
    conn = get_connection("scheduler", db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_runs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name      TEXT NOT NULL,
            scheduled_for REAL,
            status        TEXT NOT NULL,
            started_at    REAL NOT NULL,
            finished_at   REAL,
            error         TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_runs_job ON scheduler_runs(job_name, started_at)")
    conn.commit()
    return conn


def start_run(
    job_name: str,
    *,
    scheduled_for: float | None = None,
    db_path: Path = _DEFAULT_DB,
) -> int:
    now = time.time()
    with _conn(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO scheduler_runs (job_name, scheduled_for, status, started_at)
            VALUES (?, ?, 'running', ?)
            """,
            (job_name, scheduled_for, now),
        )
        return int(cursor.lastrowid)


def finish_run(
    run_id: int,
    status: str,
    *,
    error: str | None = None,
    db_path: Path = _DEFAULT_DB,
) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            """
            UPDATE scheduler_runs
            SET status = ?, finished_at = ?, error = ?
            WHERE id = ?
            """,
            (status, time.time(), error, run_id),
        )


def list_runs(
    *,
    job_name: str | None = None,
    limit: int = 50,
    db_path: Path = _DEFAULT_DB,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM scheduler_runs"
    params: list[Any] = []
    if job_name:
        query += " WHERE job_name = ?"
        params.append(job_name)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(int(limit))
    with _conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
