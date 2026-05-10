from __future__ import annotations

from typing import Any

from src.core.repository_base import RepositoryBase
from src.repositories._backends import get_user_backend


class UserPreferencesRepository:
    """Repository for flexible, namespaced user preference payloads."""

    def __init__(self, backend: RepositoryBase | None = None):
        self._backend = backend or get_user_backend()

    def get(self, user_id: str, namespace: str) -> dict[str, Any]:
        namespace = _validate_namespace(namespace)
        payload = self._backend.get_user_preference(user_id, namespace, default={})
        return dict(payload or {})

    def set(self, user_id: str, namespace: str, payload: dict[str, Any]) -> None:
        namespace = _validate_namespace(namespace)
        _validate_payload(payload)
        self._backend.set_user_preference(user_id, namespace, dict(payload))

    def patch(self, user_id: str, namespace: str, partial: dict[str, Any]) -> dict[str, Any]:
        namespace = _validate_namespace(namespace)
        _validate_payload(partial)
        if hasattr(self._backend, "patch_user_preference"):
            return dict(self._backend.patch_user_preference(user_id, namespace, dict(partial)))
        payload = {**self.get(user_id, namespace), **partial}
        self.set(user_id, namespace, payload)
        return payload


_repo = UserPreferencesRepository()


def get(user_id: str, namespace: str) -> dict[str, Any]:
    return _repo.get(user_id, namespace)


def set(user_id: str, namespace: str, payload: dict[str, Any]) -> None:
    _repo.set(user_id, namespace, payload)


def patch(user_id: str, namespace: str, partial: dict[str, Any]) -> dict[str, Any]:
    return _repo.patch(user_id, namespace, partial)


def _validate_namespace(namespace: str) -> str:
    namespace = str(namespace or "").strip()
    if not namespace:
        raise ValueError("namespace is required")
    return namespace


def _validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
