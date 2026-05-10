import json
import os
from pathlib import Path
from typing import Any

from src.core.repository_base import RepositoryBase

_BASE = Path(__file__).parents[3] / "data" / "users"


class JsonBackend(RepositoryBase):
    """Stores each user's data as JSON files under data/users/{user_id}/."""

    def __init__(self, base_dir: Path | None = None):
        self._base = base_dir or _BASE

    def _path(self, user_id: str, key: str) -> Path:
        p = self._base / user_id
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
        user_dir = self._base / user_id
        if user_dir.exists():
            shutil.rmtree(user_dir)

    def get_user_preference(self, user_id: str, namespace: str, default: Any = None) -> Any:
        return self.get(user_id, _user_preference_key(namespace), default=default)

    def set_user_preference(self, user_id: str, namespace: str, payload: dict[str, Any]) -> None:
        self.save(user_id, _user_preference_key(namespace), payload)

    def patch_user_preference(self, user_id: str, namespace: str, partial: dict[str, Any]) -> dict[str, Any]:
        payload = self.get_user_preference(user_id, namespace, default={}) or {}
        payload = {**payload, **partial}
        self.set_user_preference(user_id, namespace, payload)
        return payload


def _user_preference_key(namespace: str) -> str:
    return f"user_preferences__{namespace.replace('/', '_')}"
