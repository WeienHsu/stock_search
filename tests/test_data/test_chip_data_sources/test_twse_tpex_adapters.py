import json
from datetime import date

from src.data.chip_data_sources import tpex_adapter, twse_adapter


def test_twse_margin_rwd_parser_handles_nested_duplicate_fields():
    payload = json.dumps(
        {
            "stat": "OK",
            "tables": [
                {"fields": ["彙總"], "data": [["x"]]},
                {
                    "fields": ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額", "今日餘額", "限額", "買進", "賣出", "現券償還", "前日餘額", "今日餘額"],
                    "data": [["2330", "台積電", "100", "50", "0", "1200", "1250", "0", "0", "36", "0", "7", "43"]],
                },
            ],
        },
        ensure_ascii=False,
    )

    records = twse_adapter._parse_twse_margin_records(payload)

    assert records[0]["代號"] == "2330"
    assert records[0]["融資今日餘額"] == "1250"
    assert records[0]["融券今日餘額"] == "43"


def test_tpex_institutional_adapter_uses_position_mapping(monkeypatch):
    row = ["6488", "環球晶"] + ["0"] * 22
    row[10] = "3,000"
    row[13] = "-1,000"
    row[22] = "500"
    row[23] = "2,500"
    payload = json.dumps({"tables": [{"fields": ["代號"] * 24, "data": [row]}]}, ensure_ascii=False)
    monkeypatch.setattr(tpex_adapter, "fetch_text", lambda url: payload)
    monkeypatch.setattr(tpex_adapter, "record_source_health", lambda *args, **kwargs: {"last_success_at": 1.0})

    source = tpex_adapter.TpexChipDataSource()
    result = source._fetch_tpex_institutional_one_day("6488", date(2026, 4, 30))

    assert result["foreign_net_lots"] == 3
    assert result["investment_trust_net_lots"] == -1
    assert result["dealer_net_lots"] == 0.5
