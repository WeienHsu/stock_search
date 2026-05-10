import pytest

from src.repositories._backends.json_backend import JsonBackend
from src.repositories.user_prefs_repo import UserPreferencesRepository
from src.repositories import user_prefs_repo as _up_module
from src.repositories.holdings_repo import get_holdings, save_holdings


@pytest.fixture
def repo(tmp_path, monkeypatch):
    backend = JsonBackend(base_dir=tmp_path)
    repo_instance = UserPreferencesRepository(backend)
    monkeypatch.setattr(_up_module, "_repo", repo_instance)
    return repo_instance


def test_get_holdings_returns_empty_list_when_none(repo):
    assert get_holdings("user-1") == []


def test_save_and_get_holdings(repo):
    items = [
        {"ticker": "2330.TW", "quantity": 1000.0, "avg_cost": 850.0},
        {"ticker": "TSLA", "quantity": 10.0, "avg_cost": 200.0},
    ]
    save_holdings("user-1", items)

    result = get_holdings("user-1")
    assert len(result) == 2
    assert result[0]["ticker"] == "2330.TW"


def test_save_holdings_normalizes_ticker_to_uppercase(repo):
    save_holdings("user-1", [{"ticker": "tsla", "quantity": 5.0, "avg_cost": 300.0}])

    result = get_holdings("user-1")
    assert result[0]["ticker"] == "TSLA"


def test_save_holdings_filters_invalid_items(repo):
    items = [
        {"ticker": "", "quantity": 100.0, "avg_cost": 10.0},
        {"ticker": "AAPL", "quantity": -1.0, "avg_cost": 150.0},
        {"ticker": "MSFT", "quantity": 5.0, "avg_cost": 300.0},
    ]
    save_holdings("user-1", items)

    result = get_holdings("user-1")
    assert len(result) == 1
    assert result[0]["ticker"] == "MSFT"


def test_save_holdings_replaces_previous_data(repo):
    save_holdings("user-1", [{"ticker": "AAPL", "quantity": 10.0, "avg_cost": 150.0}])
    save_holdings("user-1", [{"ticker": "MSFT", "quantity": 5.0, "avg_cost": 300.0}])

    result = get_holdings("user-1")
    assert len(result) == 1
    assert result[0]["ticker"] == "MSFT"


def test_user_id_isolation(repo):
    save_holdings("user-1", [{"ticker": "AAPL", "quantity": 10.0, "avg_cost": 150.0}])
    save_holdings("user-2", [{"ticker": "TSLA", "quantity": 5.0, "avg_cost": 200.0}])

    assert get_holdings("user-1")[0]["ticker"] == "AAPL"
    assert get_holdings("user-2")[0]["ticker"] == "TSLA"
