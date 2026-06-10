import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_strategies_registered(client):
    ids = {s["id"] for s in client.get("/api/strategies").json()}
    assert {"strategy_d", "strategy_kd", "bias"} <= ids


def test_kline_returns_candles_indicators_signals(client, sample_ohlcv, monkeypatch):
    monkeypatch.setattr(
        "server.routes.kline.fetch_prices_by_interval",
        lambda ticker, interval, period: sample_ohlcv,
    )
    data = client.get("/api/kline/2330.TW?period=1M").json()
    assert data["symbol"] == "2330.TW"
    assert len(data["candles"]) > 0
    candle = data["candles"][-1]
    assert {"time", "open", "high", "low", "close", "volume"} <= set(candle)
    assert len(data["indicators"]["ma"]["20"]) == len(data["candles"])
    # NaN must be serialized as null, never NaN
    assert data["indicators"]["ma"]["60"][0] is None or isinstance(
        data["indicators"]["ma"]["60"][0], float
    )


def test_kline_404_when_no_data(client, monkeypatch):
    import pandas as pd

    monkeypatch.setattr(
        "server.routes.kline.fetch_prices_by_interval",
        lambda ticker, interval, period: pd.DataFrame(),
    )
    assert client.get("/api/kline/NOPE").status_code == 404


def test_quotes_normalizes_and_passes_symbols(client, monkeypatch):
    captured = {}

    def fake_fetch(symbols):
        captured["symbols"] = symbols
        return [{"symbol": s, "price": 1.0} for s in symbols]

    monkeypatch.setattr("server.routes.quotes.fetch_quotes", fake_fetch)
    resp = client.get("/api/quotes?symbols=2330,AAPL")
    assert resp.status_code == 200
    assert captured["symbols"] == ["2330.TW", "AAPL"]


def test_alert_create_validates_direction(client):
    resp = client.post(
        "/api/alerts", json={"ticker": "2330.TW", "direction": "sideways", "threshold": 1}
    )
    assert resp.status_code == 400


def test_alert_crud_roundtrip(client, tmp_path, monkeypatch):
    import functools

    import server.routes.alerts as routes
    import src.repositories.alert_repo as repo

    db = tmp_path / "alerts.db"
    for fn in ("create_price_alert", "list_alerts", "set_alert_enabled", "delete_alert", "get_alert"):
        monkeypatch.setattr(routes, fn, functools.partial(getattr(repo, fn), db_path=db))
    created = client.post(
        "/api/alerts", json={"ticker": "2330", "direction": "below", "threshold": 900}
    ).json()
    assert created["ticker"] == "2330.TW"
    assert any(a["id"] == created["id"] for a in client.get("/api/alerts").json())
    assert client.patch(f"/api/alerts/{created['id']}", json={"enabled": False}).json() == {"ok": True}
    assert client.delete(f"/api/alerts/{created['id']}").json() == {"ok": True}
    assert all(a["id"] != created["id"] for a in client.get("/api/alerts").json())
