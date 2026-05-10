import sqlite3

import pytest

from src.repositories._backends.json_backend import JsonBackend
from src.repositories._backends.pickle_backend import PickleBackend
from src.repositories._backends.sqlite_backend import SqliteBackend
from src.repositories.user_prefs_repo import UserPreferencesRepository


@pytest.fixture(params=["sqlite", "pickle", "json"])
def repo(request, tmp_path):
    if request.param == "sqlite":
        backend = SqliteBackend(db_path=tmp_path / "users.db")
    elif request.param == "pickle":
        backend = PickleBackend(subdir="user_prefs_test", base_dir=tmp_path)
    else:
        backend = JsonBackend(base_dir=tmp_path)
    return UserPreferencesRepository(backend)


def test_get_missing_namespace_returns_empty_dict(repo):
    assert repo.get("user-1", "ui") == {}


def test_set_and_get_payload(repo):
    repo.set("user-1", "ui", {"theme": "dark", "density": "compact"})

    assert repo.get("user-1", "ui") == {"theme": "dark", "density": "compact"}


def test_patch_merges_shallow_payload(repo):
    repo.set("user-1", "ui", {"theme": "morandi", "density": "default"})

    updated = repo.patch("user-1", "ui", {"theme": "dark"})

    assert updated == {"theme": "dark", "density": "default"}
    assert repo.get("user-1", "ui") == updated


def test_namespace_isolation(repo):
    repo.set("user-1", "ui", {"theme": "dark"})
    repo.set("user-1", "onboarding", {"risk": "balanced"})

    assert repo.get("user-1", "ui") == {"theme": "dark"}
    assert repo.get("user-1", "onboarding") == {"risk": "balanced"}


def test_user_isolation(repo):
    repo.set("local", "ui", {"theme": "dark"})
    repo.set("test", "ui", {"theme": "morandi"})

    assert repo.get("local", "ui") == {"theme": "dark"}
    assert repo.get("test", "ui") == {"theme": "morandi"}


def test_payload_must_be_dict(repo):
    with pytest.raises(TypeError):
        repo.set("user-1", "ui", ["dark"])  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        repo.patch("user-1", "ui", ["dark"])  # type: ignore[arg-type]


def test_namespace_is_required(repo):
    with pytest.raises(ValueError):
        repo.get("user-1", "")


def test_sqlite_backend_uses_user_preferences_table(tmp_path):
    db_path = tmp_path / "users.db"
    repo = UserPreferencesRepository(SqliteBackend(db_path=db_path))

    repo.set("user-1", "ui", {"theme": "dark"})

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT payload FROM user_preferences WHERE user_id = ? AND namespace = ?",
            ("user-1", "ui"),
        ).fetchone()
    assert row is not None
    assert '"theme": "dark"' in row[0]
