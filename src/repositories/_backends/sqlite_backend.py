"""SQLite backend — Phase 3 placeholder. Interface is frozen; implement when needed."""
from typing import Any
from src.core.repository_base import RepositoryBase


class SqliteBackend(RepositoryBase):
    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        raise NotImplementedError("SqliteBackend is a Phase 3 placeholder.")

    def save(self, user_id: str, key: str, value: Any) -> None:
        raise NotImplementedError

    def delete(self, user_id: str, key: str) -> None:
        raise NotImplementedError

    def exists(self, user_id: str, key: str) -> bool:
        raise NotImplementedError
