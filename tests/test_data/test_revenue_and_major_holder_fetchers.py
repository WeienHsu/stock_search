import json

import pandas as pd

from src.data import major_holder_fetcher, revenue_fetcher
from src.data.chip_data_sources.base import ChipResult, SourceStatus


def test_parse_mops_revenue_html_extracts_period_revenue_and_yoy():
    html = """
    <table>
      <tr><th>資料年月</th><th>營業收入淨額</th><th>去年同月增減%</th></tr>
      <tr><td>115/04</td><td>123,456</td><td>12.34</td></tr>
    </table>
    """

    rows = revenue_fetcher.parse_mops_revenue_html(html)

    assert rows[0]["period"] == "2026-04"
    assert rows[0]["revenue"] == 123456
    assert rows[0]["yoy_pct"] == 12.34


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


def test_monthly_revenue_prefers_chain_result(monkeypatch):
    monkeypatch.setattr(revenue_fetcher, "get_market_cache", lambda key, ttl_override=None: None)
    saved = {}
    monkeypatch.setattr(revenue_fetcher, "save_market_cache", lambda key, value: saved.update({key: value}))

    class DummyChain:
        def fetch_monthly_revenue(self, ticker, months):
            return ChipResult(
                pd.DataFrame([
                    {"period": "2026-04", "revenue": 123456.0, "yoy_pct": 12.3, "source": "FinMind"}
                ]),
                SourceStatus("revenue_finmind", "ok", last_success_at=1.0),
            )

    monkeypatch.setattr(revenue_fetcher, "build_default_chain", lambda: DummyChain())

    df = revenue_fetcher.fetch_monthly_revenue("2330.TW", months=12)

    assert not df.empty
    assert df.iloc[0]["revenue"] == 123456.0
    assert "revenue_v2_2330_12" in saved


def test_holder_snapshot_to_frame_returns_empty_when_missing_value():
    assert major_holder_fetcher.holder_snapshot_to_frame({"foreign_holding_pct": None}).empty
