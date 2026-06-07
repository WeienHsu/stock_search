"""Apply pending SQL migrations in migrations/ against the PostgreSQL database.

Runs every migrations/*.sql file in filename order, skipping ones already
recorded in the schema_migrations table. Each file runs in its own transaction:
on error it rolls back and stops, leaving prior migrations applied.

Connects directly via DATABASE_URL with psycopg2 (raw SQL, no SQLite->Postgres
translation), so .sql files are executed exactly as written.

Usage:
    python scripts/apply_migrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _applied(cur) -> set[str]:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    cur.execute("SELECT filename FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def main() -> None:
    import psycopg2

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        sys.exit("DATABASE_URL is not set; cannot apply migrations.")

    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migrations found.")
        return

    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            done = _applied(cur)
            conn.commit()

        pending = [f for f in files if f.name not in done]
        if not pending:
            print(f"Up to date ({len(done)} migration(s) already applied).")
            return

        for path in pending:
            print(f"Applying {path.name} ...", end=" ", flush=True)
            with conn.cursor() as cur:
                cur.execute(path.read_text())
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (path.name,),
                )
            conn.commit()
            print("ok")

        print(f"Done. Applied {len(pending)} migration(s).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
