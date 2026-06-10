from src.data import major_holder_fetcher
from src.data.chip_data_sources.base import ChipResult, SourceStatus


def test_major_holder_snapshot_uses_chain_result(monkeypatch):
    monkeypatch.setattr(major_holder_fetcher, "get_market_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(major_holder_fetcher, "save_market_cache", lambda key, value: None)

    class DummyChain:
        def fetch_shareholding_snapshot(self, ticker):
            return ChipResult(
                {
                    "supported": True,
                    "ticker": ticker,
                    "code": "2330",
                    "foreign_holding_pct": 72.34,
                    "source": "FinMind",
                },
                SourceStatus("chip_finmind", "ok", last_success_at=1.0),
            )

    monkeypatch.setattr(major_holder_fetcher, "build_default_chain", lambda: DummyChain())

    result = major_holder_fetcher.fetch_major_holder_snapshot("2330.TW")

    assert result["foreign_holding_pct"] == 72.34
    assert result["source"] == "FinMind"


def test_major_holder_snapshot_ignores_unavailable_cache(monkeypatch):
    monkeypatch.setattr(
        major_holder_fetcher,
        "get_market_cache",
        lambda key, ttl_override=None: {"foreign_holding_pct": None, "message": "stale unavailable"},
    )
    monkeypatch.setattr(major_holder_fetcher, "save_market_cache", lambda key, value: None)

    class DummyChain:
        def fetch_shareholding_snapshot(self, ticker):
            return ChipResult(
                {
                    "supported": True,
                    "ticker": ticker,
                    "code": "2330",
                    "foreign_holding_pct": 70.67,
                    "source": "FinMind",
                },
                SourceStatus("chip_finmind", "ok", last_success_at=1.0),
            )

    monkeypatch.setattr(major_holder_fetcher, "build_default_chain", lambda: DummyChain())

    result = major_holder_fetcher.fetch_major_holder_snapshot("2330.TW")

    assert result["foreign_holding_pct"] == 70.67


