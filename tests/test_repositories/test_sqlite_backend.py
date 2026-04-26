import pytest

from src.repositories._backends.sqlite_backend import SqliteBackend


@pytest.fixture
def backend(tmp_path):
    return SqliteBackend(db_path=tmp_path / "test.db")


def test_get_missing_returns_default(backend):
    assert backend.get("u1", "k") is None
    assert backend.get("u1", "k", default=42) == 42


def test_save_and_get(backend):
    backend.save("u1", "watchlist", [{"ticker": "TSLA"}])
    assert backend.get("u1", "watchlist") == [{"ticker": "TSLA"}]


def test_overwrite(backend):
    backend.save("u1", "prefs", {"show_macd": True})
    backend.save("u1", "prefs", {"show_macd": False})
    assert backend.get("u1", "prefs") == {"show_macd": False}


def test_user_isolation(backend):
    backend.save("u1", "key", "value_for_u1")
    backend.save("u2", "key", "value_for_u2")
    assert backend.get("u1", "key") == "value_for_u1"
    assert backend.get("u2", "key") == "value_for_u2"


def test_exists(backend):
    assert not backend.exists("u1", "k")
    backend.save("u1", "k", 1)
    assert backend.exists("u1", "k")


def test_delete(backend):
    backend.save("u1", "k", "v")
    backend.delete("u1", "k")
    assert not backend.exists("u1", "k")


def test_delete_nonexistent_is_safe(backend):
    backend.delete("u1", "missing")  # should not raise
