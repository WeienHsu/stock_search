import json
from datetime import date

import pandas as pd

from src.data import chip_fetcher
from src.data.chip_data_sources.base import ChipResult, SourceStatus


def test_market_kind_only_supports_taiwan_tickers():
    assert chip_fetcher.market_kind("2330.TW") == "twse"
    assert chip_fetcher.market_kind("6488.TWO") == "tpex"
    assert chip_fetcher.market_kind("TSLA") == "unsupported"


def test_fetch_twse_institutional_one_day_filters_ticker(monkeypatch):
    payload = json.dumps(
        {
            "stat": "OK",
            "fields": [
                "證券代號",
                "外陸資買賣超股數(不含外資自營商)",
                "投信買賣超股數",
                "自營商買賣超股數",
                "三大法人買賣超股數",
            ],
            "data": [["2330", "2,000", "1,000", "-500", "2,500"]],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(chip_fetcher, "fetch_text", lambda url: payload)

    result = chip_fetcher._fetch_twse_institutional_one_day("2330", date(2026, 4, 30))

    assert result["foreign_net_lots"] == 2
    assert result["investment_trust_net_lots"] == 1
    assert result["dealer_net_lots"] == -0.5


def test_fetch_tpex_institutional_one_day_uses_position_mapping(monkeypatch):
    row = ["6488", "name"] + ["0"] * 22
    row[10] = "3,000"
    row[13] = "-1,000"
    row[22] = "500"
    row[23] = "2,500"
    payload = json.dumps({"tables": [{"fields": ["代號"] * 24, "data": [row]}]}, ensure_ascii=False)
    monkeypatch.setattr(chip_fetcher, "fetch_text", lambda url: payload)

    result = chip_fetcher._fetch_tpex_institutional_one_day("6488", date(2026, 4, 30))

    assert result["foreign_net_lots"] == 3
    assert result["investment_trust_net_lots"] == -1
    assert result["dealer_net_lots"] == 0.5


def test_fetch_twse_margin_latest_parses_json_list(monkeypatch):
    payload = json.dumps(
        [{
            "股票代號": "2330",
            "融資買進": "100",
            "融資賣出": "50",
            "融資今日餘額": "12,827",
            "融券賣出": "36",
            "融券今日餘額": "43",
        }],
        ensure_ascii=False,
    )
    monkeypatch.setattr(chip_fetcher, "fetch_text", lambda url: payload)

    result = chip_fetcher._fetch_twse_margin_latest("2330")

    assert result["margin_balance"] == 12827
    assert result["short_balance"] == 43


def test_summarize_chip_data_counts_institutional_and_margin_change():
    institutional = pd.DataFrame({
        "foreign_net_lots": [2, -1, 3],
        "investment_trust_net_lots": [1, 1, -0.5],
        "dealer_net_lots": [0.5, 0.5, -1],
    })
    margin = pd.DataFrame({"margin_balance": [100, 110, 125]})

    summary = chip_fetcher.summarize_chip_data(institutional, margin)

    assert summary["foreign_5d_lots"] == 4
    assert summary["investment_trust_5d_lots"] == 1.5
    assert summary["margin_change_lots"] == 25
    assert summary["margin_change_pct"] == 25
    assert summary["margin_trend"] == "增加"


def test_fetch_chip_snapshot_hides_unsupported_ticker():
    result = chip_fetcher.fetch_chip_snapshot("GOOGL")

    assert result == {"supported": False, "ticker": "GOOGL", "market": "unsupported", "message": "僅支援台股"}


def test_fetch_today_uses_latest_data_date(monkeypatch):
    monkeypatch.setattr(
        chip_fetcher,
        "fetch_chip_snapshot",
        lambda ticker: {
            "supported": True,
            "ticker": ticker,
            "institutional": pd.DataFrame([
                {"date": "2026-04-29", "foreign_net_lots": 1, "investment_trust_net_lots": 2, "dealer_net_lots": 3}
            ]),
            "margin": pd.DataFrame([
                {"date": "2026-04-30", "margin_balance": 100, "short_balance": 5}
            ]),
            "major_holder": {"date": "2026-04-28", "foreign_holding_pct": 72.34},
            "source_statuses": {},
        },
    )

    result = chip_fetcher.fetch_today("2330.TW")

    assert result["date"] == "2026-04-30"


def test_fetch_institutional_trades_skips_probable_taiwan_etf():
    result = chip_fetcher.fetch_institutional_trades("0050.TW")

    assert result.empty


def test_fetch_chip_snapshot_does_not_cache_partial_failure(monkeypatch):
    monkeypatch.setattr(chip_fetcher, "get_chip_cache", lambda key, ttl_override=None: None)
    saved = {}
    monkeypatch.setattr(chip_fetcher, "save_chip_cache", lambda key, value: saved.update({key: value}))

    class DummyChain:
        def fetch_institutional_history(self, ticker, days):
            return ChipResult(
                pd.DataFrame(),
                SourceStatus("chip_finmind", "unavailable", "HTTP Error 400: Bad Request", last_success_at=1.0),
            )

        def fetch_margin_history(self, ticker, days):
            return ChipResult(
                pd.DataFrame([{"date": "2026-04-30", "margin_balance": 100, "short_balance": 1}]),
                SourceStatus("chip_twse_margn", "ok", last_success_at=1.0),
            )

    monkeypatch.setattr(chip_fetcher, "build_default_chain", lambda: DummyChain())
    monkeypatch.setattr(
        chip_fetcher,
        "_safe_major_holder_snapshot",
        lambda ticker: {
            "supported": True,
            "ticker": ticker,
            "foreign_holding_pct": None,
            "message": "外資持股資料暫不可用",
            "source": "chip_finmind",
        },
    )

    result = chip_fetcher.fetch_chip_snapshot("2330.TW")

    assert result["source_statuses"]["institutional"]["status"] == "unavailable"
    assert saved == {}
