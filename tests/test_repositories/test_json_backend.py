import pytest
from src.repositories._backends.json_backend import JsonBackend


@pytest.fixture
def backend(tmp_path, monkeypatch):
    import src.repositories._backends.json_backend as mod
    monkeypatch.setattr(mod, "_BASE", tmp_path / "users")
    return JsonBackend()


def test_save_and_get(backend):
    backend.save("test_user", "watchlist", [{"ticker": "TSLA"}])
    result = backend.get("test_user", "watchlist")
    assert result == [{"ticker": "TSLA"}]


def test_get_default(backend):
    assert backend.get("nobody", "nothing", default=42) == 42


def test_exists(backend):
    assert not backend.exists("u", "k")
    backend.save("u", "k", {"a": 1})
    assert backend.exists("u", "k")


def test_delete(backend):
    backend.save("u", "k", "value")
    backend.delete("u", "k")
    assert not backend.exists("u", "k")


def test_user_isolation(backend):
    backend.save("alice", "prefs", {"x": 1})
    backend.save("bob",   "prefs", {"x": 2})
    assert backend.get("alice", "prefs")["x"] == 1
    assert backend.get("bob",   "prefs")["x"] == 2
