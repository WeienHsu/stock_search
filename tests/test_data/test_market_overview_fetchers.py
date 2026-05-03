import json
from datetime import date

import pandas as pd

from src.data import index_fetcher, market_sentiment_fetcher, taifex_fetcher, twse_fetcher


def test_ma_alignment_score_counts_ordered_averages():
    df = pd.DataFrame(
        {
            "close": [100],
            "MA_5": [120],
            "MA_10": [110],
            "MA_20": [100],
            "MA_60": [90],
        }
    )

    assert index_fetcher.ma_alignment_score(df) == 4


def test_index_snapshot_classifies_kd_macd_and_volume():
    df = pd.DataFrame(
        {
            "date": ["2026-04-29", "2026-04-30"],
            "close": [100, 105],
            "volume": [1000, 2000],
            "K": [50, 85],
            "D": [50, 82],
            "histogram": [-1, 1],
            "MA_5": [120, 120],
            "MA_10": [110, 110],
            "MA_20": [100, 100],
            "MA_60": [90, 90],
        }
    )

    snapshot = index_fetcher.index_snapshot(df)

    assert snapshot["change_pct"] == 5
    assert snapshot["kd_status"] == "超買"
    assert snapshot["macd_status"] == "多頭"
    assert snapshot["ma_score"] == 4


def test_twse_to_float_handles_commas_and_empty_values():
    assert twse_fetcher._to_float("1,234") == 1234
    assert twse_fetcher._to_float("") == 0
    assert twse_fetcher._to_float(None) == 0


def test_fetch_twse_t86_aggregates_foreign_and_investment(monkeypatch):
    payload = json.dumps(
        {
            "stat": "OK",
            "fields": ["證券代號", "外陸資買賣超股數(不含外資自營商)", "投信買賣超股數"],
            "data": [["2330", "1,000", "200"], ["2317", "-500", "300"]],
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(twse_fetcher, "fetch_text", lambda url: payload)

    result = twse_fetcher._fetch_twse_t86(date(2026, 4, 30))

    assert result == {"foreign_net_shares": 500, "investment_trust_net_shares": 500}


def test_fetch_tpex_daily_trade_uses_position_mapping(monkeypatch):
    payload = json.dumps(
        {
            "tables": [
                {
                    "fields": ["代號"] * 24,
                    "data": [
                        ["006201", "name", "0", "0", "0", "0", "0", "0", "0", "0", "1,500", "0", "0", "-200"]
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(twse_fetcher, "fetch_text", lambda url: payload)

    result = twse_fetcher._fetch_tpex_daily_trade(date(2026, 4, 30))

    assert result == {"foreign_net_shares": 1500, "investment_trust_net_shares": -200}


def test_taifex_one_day_extracts_foreign_open_interest(monkeypatch):
    html = """
    <table>
      <tr>
        <td>1</td><td>臺股期貨</td><td>外資</td>
        <td>70,159</td><td>554,377,821</td>
        <td>67,153</td><td>530,626,691</td>
        <td>3,006</td><td>23,751,130</td>
        <td>19,569</td><td>154,006,546</td>
        <td>63,613</td><td>500,605,400</td>
        <td>-44,044</td><td>-346,598,854</td>
      </tr>
    </table>
    """
    monkeypatch.setattr(taifex_fetcher, "fetch_text", lambda url, data=None: html)

    result = taifex_fetcher._fetch_one_day(date(2026, 4, 30))

    assert result["foreign_oi_net_contracts"] == -44044
    assert result["foreign_oi_long_contracts"] == 19569
    assert result["foreign_oi_short_contracts"] == 63613


def test_market_sentiment_fetchers_save_parsed_results(monkeypatch):
    saved = {}
    monkeypatch.setattr(market_sentiment_fetcher, "get_market_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(market_sentiment_fetcher, "save_market_cache", lambda key, value: saved.update({key: value}))
    monkeypatch.setattr(
        market_sentiment_fetcher,
        "fetch_text",
        lambda url: json.dumps(
            {
                "fear_and_greed": {"score": 66.6, "rating": "greed", "timestamp": "2026-05-01T00:00:00+00:00"},
                "fear_and_greed_historical": {"data": [{"x": 1, "y": 66.6}]},
            }
        ),
    )

    result = market_sentiment_fetcher.fetch_cnn_fear_greed()

    assert result["score"] == 66.6
    assert saved["cnn_fear_greed"]["rating"] == "greed"
