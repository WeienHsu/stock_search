import os

from src.repositories._backends.json_backend import JsonBackend
from src.repositories._backends.sqlite_backend import SqliteBackend
from src.core.repository_base import RepositoryBase


def get_user_backend() -> RepositoryBase:
    """Return the configured user-data backend (json or sqlite)."""
    if os.getenv("STORAGE_BACKEND", "json").lower() == "sqlite":
        return SqliteBackend()
    return JsonBackend()
