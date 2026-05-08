from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from src.data.chip_data_sources import build_default_chain
from src.data.chip_utils import is_probable_taiwan_etf, is_taiwan_ticker, ticker_code
from src.data.data_source_probe import SimpleTableParser, fetch_text
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache
from src.repositories.source_health_repo import record_source_health

_DAY = 24 * 3600


@st.cache_data(ttl=600, show_spinner=False)
def fetch_monthly_revenue(ticker: str, months: int = 12) -> pd.DataFrame:
    if not is_taiwan_ticker(ticker):
        return pd.DataFrame()
    if is_probable_taiwan_etf(ticker):
        record_source_health("revenue_finmind", "unsupported", reason="ETF 沒有公司月營收資料")
        return pd.DataFrame()
    code = ticker_code(ticker)
    cache_key = f"revenue_v2_{code}_{months}"
    cached = get_market_cache(cache_key, ttl_override=7 * _DAY)
    if isinstance(cached, pd.DataFrame) and not cached.empty:
        source = str(cached["source"].iloc[-1]) if "source" in cached.columns else "revenue_mops"
        if source not in {"revenue_finmind", "revenue_mops"}:
            source = "revenue_mops"
        record_source_health(source, "ok")
        return cached

    chain = build_default_chain()
    finmind = chain.fetch_monthly_revenue(ticker, months)
    if isinstance(finmind.data, pd.DataFrame) and not finmind.data.empty:
        df = finmind.data.sort_values("period").reset_index(drop=True)
        save_market_cache(cache_key, df)
        return df

    rows: list[dict[str, Any]] = []
    current = date.today()
    roc_year = current.year - 1911
    month = current.month
    for _ in range(months + 4):
        if len(rows) >= months:
            break
        record = _fetch_mops_monthly_revenue(code, roc_year, month)
        if record:
            rows.append(record)
        month -= 1
        if month <= 0:
            month = 12
            roc_year -= 1

    df = pd.DataFrame(rows).sort_values("period").reset_index(drop=True) if rows else pd.DataFrame()
    if not df.empty:
        df.loc[:, "source"] = "revenue_mops"
        save_market_cache(cache_key, df)
        record_source_health("revenue_mops", "ok")
    else:
        record_source_health("revenue_mops", "unavailable", reason="MOPS monthly revenue unavailable")
    return df


def _fetch_mops_monthly_revenue(code: str, roc_year: int, month: int) -> dict[str, Any] | None:
    url = "https://mops.twse.com.tw/mops/web/ajax_t05st10_ifrs"
    try:
        html = fetch_text(
            url,
            data={
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "off": "1",
                "queryName": "co_id",
                "inpuType": "co_id",
                "TYPEK": "all",
                "co_id": code,
                "year": str(roc_year),
                "month": str(month),
            },
        )
        records = parse_mops_revenue_html(html)
    except Exception:
        return None
    return records[0] if records else None


def parse_mops_revenue_html(html: str) -> list[dict[str, Any]]:
    parser = SimpleTableParser()
    parser.feed(html)
    records = []
    for row in parser.rows:
        text = " ".join(row)
        if len(row) < 3 or "累計" in text:
            continue
        period = _find_period(row)
        revenue = _first_number(row)
        yoy = _first_percent(row)
        if period and revenue is not None:
            records.append({
                "period": period,
                "revenue": revenue,
                "yoy_pct": yoy,
                "raw": row,
            })
    return records


def _find_period(row: list[str]) -> str:
    for cell in row:
        text = cell.replace("/", "-")
        parts = text.split("-")
        if len(parts) >= 2 and all(part.isdigit() for part in parts[:2]):
            year = int(parts[0])
            if year < 1911:
                year += 1911
            return f"{year:04d}-{int(parts[1]):02d}"
    return ""


def _first_number(row: list[str]) -> float | None:
    for cell in row:
        value = _to_float(cell)
        if value is not None and abs(value) > 100:
            return value
    return None


def _first_percent(row: list[str]) -> float | None:
    for cell in reversed(row):
        if "%" in cell or "." in cell:
            value = _to_float(cell.replace("%", ""))
            if value is not None and -1000 < value < 1000:
                return value
    return None


def _to_float(value: str) -> float | None:
    text = str(value).strip().replace(",", "")
    if not text or text in {"--", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None
