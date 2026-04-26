import json
import os
from pathlib import Path
from typing import Any

from src.core.repository_base import RepositoryBase

_BASE = Path(__file__).parents[3] / "data" / "users"


class JsonBackend(RepositoryBase):
    """Stores each user's data as JSON files under data/users/{user_id}/."""

    def _path(self, user_id: str, key: str) -> Path:
        p = _BASE / user_id
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{key}.json"

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        path = self._path(user_id, key)
        if not path.exists():
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, user_id: str, key: str, value: Any) -> None:
        path = self._path(user_id, key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

    def delete(self, user_id: str, key: str) -> None:
        path = self._path(user_id, key)
        if path.exists():
            path.unlink()

    def exists(self, user_id: str, key: str) -> bool:
        return self._path(user_id, key).exists()

    def purge_user(self, user_id: str) -> None:
        import shutil
        user_dir = _BASE / user_id
        if user_dir.exists():
            shutil.rmtree(user_dir)
