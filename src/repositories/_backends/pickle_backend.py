import pickle
import time
from pathlib import Path
from typing import Any

from src.core.repository_base import RepositoryBase

_BASE = Path(__file__).parents[3] / "data" / "cache"


class PickleBackend(RepositoryBase):
    """
    Stores large objects (DataFrames) as pickle files under data/cache/{user_id}/.
    Supports TTL via a sidecar .meta file.
    """

    def __init__(self, subdir: str = "prices", base_dir: Path | None = None):
        self._subdir = subdir
        self._base = base_dir or _BASE

    def _path(self, user_id: str, key: str) -> Path:
        safe_key = key.replace("/", "_")
        p = self._base / self._subdir / user_id
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{safe_key}.pkl"

    def _meta_path(self, user_id: str, key: str) -> Path:
        return self._path(user_id, key).with_suffix(".meta")

    def is_fresh(self, user_id: str, key: str, ttl_seconds: int = 21600) -> bool:
        meta = self._meta_path(user_id, key)
        if not meta.exists():
            return False
        saved_at = float(meta.read_text())
        return (time.time() - saved_at) < ttl_seconds

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        path = self._path(user_id, key)
        if not path.exists():
            return default
        with open(path, "rb") as f:
            return pickle.load(f)

    def save(self, user_id: str, key: str, value: Any) -> None:
        path = self._path(user_id, key)
        with open(path, "wb") as f:
            pickle.dump(value, f)
        self._meta_path(user_id, key).write_text(str(time.time()))

    def delete(self, user_id: str, key: str) -> None:
        for path in [self._path(user_id, key), self._meta_path(user_id, key)]:
            if path.exists():
                path.unlink()

    def clear_user(self, user_id: str) -> int:
        cache_dir = self._base / self._subdir / user_id
        if not cache_dir.exists():
            return 0
        deleted = 0
        for path in cache_dir.iterdir():
            if path.is_file():
                path.unlink()
                deleted += 1
        try:
            cache_dir.rmdir()
        except OSError:
            pass
        return deleted

    def exists(self, user_id: str, key: str) -> bool:
        return self._path(user_id, key).exists()

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
    return f"user_preferences__{namespace}"
