from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from src.data.data_source_probe import fetch_text, parse_taifex_futures_html
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache


def fetch_taifex_txf_open_interest(days: int = 10) -> pd.DataFrame:
    cache_key = f"taifex_txf_oi_{days}"
    cached = get_market_cache(cache_key, ttl_override=6 * 3600)
    if isinstance(cached, pd.DataFrame) and not cached.empty:
        return cached

    rows = []
    for current in _recent_dates(days * 2 + 8):
        if len(rows) >= days:
            break
        record = _fetch_one_day(current)
        if record:
            rows.append(record)

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True) if rows else pd.DataFrame()
    if not df.empty:
        save_market_cache(cache_key, df)
    return df


def _fetch_one_day(current: date) -> dict[str, Any] | None:
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"
    try:
        html = fetch_text(
            url,
            data={
                "queryDate": current.strftime("%Y/%m/%d"),
                "commodityId": "TXF",
                "button": "送出查詢",
            },
        )
        records = parse_taifex_futures_html(html)
    except Exception:
        return None
    foreign = next((row for row in records if row.get("identity") == "外資"), None)
    if not foreign:
        return None
    return {
        "date": current.strftime("%Y-%m-%d"),
        "foreign_oi_net_contracts": _to_float(foreign.get("open_interest_net_contracts")),
        "foreign_oi_long_contracts": _to_float(foreign.get("open_interest_long_contracts")),
        "foreign_oi_short_contracts": _to_float(foreign.get("open_interest_short_contracts")),
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
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0
