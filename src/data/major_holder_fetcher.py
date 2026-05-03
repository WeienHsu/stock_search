from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.chip_fetcher import is_taiwan_ticker, market_kind, ticker_code
from src.data.data_source_probe import fetch_text, parse_json_list, parse_tpex_table, parse_twse_rwd_table
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache

_DAY = 24 * 3600


def fetch_major_holder_snapshot(ticker: str) -> dict[str, Any]:
    if not is_taiwan_ticker(ticker):
        return {"supported": False, "ticker": ticker, "message": "僅支援台股"}
    code = ticker_code(ticker)
    kind = market_kind(ticker)
    cache_key = f"major_holder_{kind}_{code}"
    cached = get_market_cache(cache_key, ttl_override=_DAY)
    if isinstance(cached, dict) and cached:
        return cached

    result = _fetch_twse_foreign_holding(code) if kind == "twse" else _fetch_tpex_foreign_holding(code)
    if result:
        save_market_cache(cache_key, result)
        return result
    return {
        "supported": True,
        "ticker": ticker,
        "code": code,
        "foreign_holding_pct": None,
        "message": "外資持股資料暫不可用",
    }


def _fetch_twse_foreign_holding(code: str) -> dict[str, Any] | None:
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/MI_QFIIS",
        "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS?response=json",
    ]
    for url in urls:
        try:
            text = fetch_text(url)
            records = _parse_twse_qfiis_records(text)
        except Exception:
            continue
        for row in records:
            row_code = str(row.get("證券代號") or row.get("股票代號") or row.get("Code") or "").strip()
            if row_code == code:
                pct = _to_float(row.get("全體外資及陸資持股比率") or row.get("外資及陸資持股比率") or row.get("ForeignInvestmentRemainingRatio"))
                return {
                    "supported": True,
                    "ticker": f"{code}.TW",
                    "code": code,
                    "foreign_holding_pct": pct,
                    "source": "TWSE_MI_QFIIS",
                }
    return None


def _fetch_tpex_foreign_holding(code: str) -> dict[str, Any] | None:
    urls = [
        "https://www.tpex.org.tw/www/zh-tw/foreign/forgHold?response=json",
        "https://www.tpex.org.tw/www/zh-tw/insti/foreigner?response=json",
    ]
    for url in urls:
        try:
            fields, rows = parse_tpex_table(fetch_text(url))
        except Exception:
            continue
        for row in rows:
            record = dict(zip(fields, row, strict=False))
            row_code = str(record.get("代號") or record.get("股票代號") or "").strip()
            if row_code == code:
                pct = _to_float(record.get("外資持股比率") or record.get("外資及陸資持股比率"))
                return {
                    "supported": True,
                    "ticker": f"{code}.TWO",
                    "code": code,
                    "foreign_holding_pct": pct,
                    "source": "TPEX_FOREIGN_HOLDING",
                }
    return None


def _parse_twse_qfiis_records(text: str) -> list[dict[str, Any]]:
    try:
        return parse_json_list(text)
    except Exception:
        fields, rows = parse_twse_rwd_table(text)
        return [dict(zip(fields, row, strict=False)) for row in rows]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text in {"--", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def holder_snapshot_to_frame(snapshot: dict[str, Any]) -> pd.DataFrame:
    if snapshot.get("foreign_holding_pct") is None:
        return pd.DataFrame()
    return pd.DataFrame([{
        "項目": "外資持股比率",
        "數值": f"{float(snapshot['foreign_holding_pct']):.2f}%",
        "來源": snapshot.get("source", ""),
    }])
