from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import pandas as pd

from src.data.data_source_probe import fetch_text, parse_json_list, parse_tpex_table, parse_twse_rwd_table
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache

_DAY = 24 * 3600


def fetch_institutional_flow(days: int = 10) -> pd.DataFrame:
    cache_key = f"institutional_flow_{days}"
    cached = get_market_cache(cache_key, ttl_override=6 * 3600)
    if isinstance(cached, pd.DataFrame) and not cached.empty:
        return cached

    rows = []
    for current in _recent_dates(days * 2 + 8):
        if len(rows) >= days:
            break
        twse = _fetch_twse_t86(current)
        tpex = _fetch_tpex_daily_trade(current)
        if twse is None and tpex is None:
            continue
        foreign = (twse or {}).get("foreign_net_shares", 0) + (tpex or {}).get("foreign_net_shares", 0)
        investment = (twse or {}).get("investment_trust_net_shares", 0) + (tpex or {}).get("investment_trust_net_shares", 0)
        rows.append({
            "date": current.strftime("%Y-%m-%d"),
            "foreign_net_shares": foreign,
            "investment_trust_net_shares": investment,
            "foreign_net_lots": foreign / 1000,
            "investment_trust_net_lots": investment / 1000,
        })

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True) if rows else pd.DataFrame()
    if not df.empty:
        save_market_cache(cache_key, df)
    return df


def fetch_margin_summary() -> dict[str, Any]:
    cache_key = "twse_margin_summary"
    cached = get_market_cache(cache_key, ttl_override=_DAY)
    if isinstance(cached, dict) and cached:
        return cached

    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    rows = parse_json_list(fetch_text(url))
    summary = {
        "records": len(rows),
        "margin_balance": sum(_to_float(row.get("融資今日餘額")) for row in rows),
        "short_balance": sum(_to_float(row.get("融券今日餘額")) for row in rows),
        "sample_date": "",
    }
    save_market_cache(cache_key, summary)
    return summary


def fetch_valuation_summary() -> dict[str, Any]:
    cache_key = "twse_valuation_summary"
    cached = get_market_cache(cache_key, ttl_override=7 * _DAY)
    if isinstance(cached, dict) and cached:
        return cached

    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d"
    rows = parse_json_list(fetch_text(url))
    pe_values = [_to_float(row.get("PEratio")) for row in rows]
    pe_values = [value for value in pe_values if value > 0]
    summary = {
        "records": len(rows),
        "median_pe": float(pd.Series(pe_values).median()) if pe_values else None,
        "average_pe": float(pd.Series(pe_values).mean()) if pe_values else None,
        "date": str(rows[0].get("Date", "")) if rows else "",
    }
    save_market_cache(cache_key, summary)
    return summary


def _fetch_twse_t86(current: date) -> dict[str, float] | None:
    ymd = current.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={ymd}&selectType=ALLBUT0999&response=json"
    try:
        fields, rows = parse_twse_rwd_table(fetch_text(url))
    except Exception:
        return None
    if not rows:
        return None
    records = [dict(zip(fields, row, strict=False)) for row in rows]
    return {
        "foreign_net_shares": sum(_to_float(row.get("外陸資買賣超股數(不含外資自營商)")) for row in records),
        "investment_trust_net_shares": sum(_to_float(row.get("投信買賣超股數")) for row in records),
    }


def _fetch_tpex_daily_trade(current: date) -> dict[str, float] | None:
    slash_date = current.strftime("%Y/%m/%d")
    url = f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?date={slash_date}&type=Daily&response=json"
    try:
        _fields, rows = parse_tpex_table(fetch_text(url))
    except Exception:
        return None
    if not rows:
        return None
    return {
        "foreign_net_shares": sum(_to_float(row[10] if len(row) > 10 else 0) for row in rows),
        "investment_trust_net_shares": sum(_to_float(row[13] if len(row) > 13 else 0) for row in rows),
    }


def _recent_dates(limit: int) -> list[date]:
    current = date.today()
    dates = []
    while len(dates) < limit:
        if current.weekday() < 5:
            dates.append(current)
        current -= timedelta(days=1)
    return dates


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0
