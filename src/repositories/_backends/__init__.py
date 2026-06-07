import os

from src.repositories._backends.json_backend import JsonBackend
from src.repositories._backends.sqlite_backend import SqliteBackend
from src.repositories._backends.postgres_backend import PostgresBackend
from src.core.repository_base import RepositoryBase


def get_user_backend() -> RepositoryBase:
    """Return the configured user-data backend (json, sqlite or postgres)."""
    backend = os.getenv("STORAGE_BACKEND", "json").lower()
    if backend == "postgres":
        return PostgresBackend()
    if backend == "sqlite":
        return SqliteBackend()
    return JsonBackend()

