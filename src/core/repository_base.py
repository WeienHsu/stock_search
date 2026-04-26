from abc import ABC, abstractmethod
from typing import Any


class RepositoryBase(ABC):
    """Pluggable storage backend interface. All user-scoped data goes through here."""

    @abstractmethod
    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        """Load a value for the given user and key."""

    @abstractmethod
    def save(self, user_id: str, key: str, value: Any) -> None:
        """Persist a value for the given user and key."""

    @abstractmethod
    def delete(self, user_id: str, key: str) -> None:
        """Remove a key for the given user."""

    @abstractmethod
    def exists(self, user_id: str, key: str) -> bool:
        """Return True if the key exists for the given user."""

    def purge_user(self, user_id: str) -> None:
        """Remove all data for the given user."""
