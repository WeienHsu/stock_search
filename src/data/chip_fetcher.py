from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.data.chip_data_sources import build_default_chain
from src.data.chip_utils import is_taiwan_ticker, market_kind, ticker_code
from src.data.data_source_probe import fetch_text, parse_json_list, parse_tpex_table, parse_twse_rwd_table
from src.data.dynamic_ttl import get_ttl
from src.repositories.chip_data_cache_repo import get_chip_cache, save_chip_cache

_DAY = 24 * 3600


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_chip_snapshot(ticker: str, institutional_days: int = 5, margin_days: int = 20) -> dict[str, Any]:
    kind = market_kind(ticker)
    if kind == "unsupported":
        return {"supported": False, "ticker": ticker, "market": kind, "message": "僅支援台股"}

    code = ticker_code(ticker)
    cache_key = f"chip_snapshot_v5_{kind}_{code}_{institutional_days}_{margin_days}"
    cached = get_chip_cache(cache_key, ttl_override=_DAY)
    if isinstance(cached, dict) and cached:
        return cached

    chain = build_default_chain()
    institutional_result = chain.fetch_institutional_history(ticker, institutional_days)
    margin_result = chain.fetch_margin_history(ticker, margin_days)
    institutional = institutional_result.data if isinstance(institutional_result.data, pd.DataFrame) else pd.DataFrame()
    margin = margin_result.data if isinstance(margin_result.data, pd.DataFrame) else pd.DataFrame()
    major_holder = _safe_major_holder_snapshot(ticker)
    summary = summarize_chip_data(institutional, margin)
    result = {
        "supported": True,
        "ticker": ticker,
        "code": code,
        "market": kind,
        "institutional": institutional,
        "margin": margin,
        "major_holder": major_holder,
        "qfiis_pct": major_holder.get("foreign_holding_pct"),
        "summary": summary,
        "source_statuses": {
            "institutional": _status_dict(institutional_result.source_status),
            "margin": _status_dict(margin_result.source_status),
            "major_holder": _safe_source_status(_safe_health_source_id(major_holder), major_holder),
        },
    }
    if _should_cache_chip_snapshot(result):
        save_chip_cache(cache_key, result)
    return result


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_institutional_trades(ticker: str, days: int = 5) -> pd.DataFrame:
    chain = build_default_chain()
    result = chain.fetch_institutional_history(ticker, days)
    if isinstance(result.data, pd.DataFrame):
        return result.data
    return pd.DataFrame()


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_margin_trend(ticker: str, days: int = 20) -> pd.DataFrame:
    chain = build_default_chain()
    result = chain.fetch_margin_history(ticker, days)
    if isinstance(result.data, pd.DataFrame):
        return result.data
    return pd.DataFrame()


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_today(ticker: str) -> dict[str, Any]:
    snapshot = fetch_chip_snapshot(ticker)
    if not snapshot.get("supported"):
        return snapshot
    institutional = snapshot.get("institutional")
    margin = snapshot.get("margin")
    major_holder = snapshot.get("major_holder") or {}
    snapshot_date = _latest_snapshot_date(institutional, margin, major_holder)
    source = snapshot.get("source_statuses", {})
    return {
        "supported": True,
        "ticker": snapshot.get("ticker", ticker).upper(),
        "date": snapshot_date,
        "institutional_foreign": _latest_numeric(institutional, "foreign_net_lots"),
        "institutional_trust": _latest_numeric(institutional, "investment_trust_net_lots"),
        "institutional_dealer": _latest_numeric(institutional, "dealer_net_lots"),
        "margin_balance": _latest_numeric(margin, "margin_balance"),
        "short_balance": _latest_numeric(margin, "short_balance"),
        "qfiis_pct": major_holder.get("foreign_holding_pct"),
        "source": source,
    }


def summarize_chip_data(institutional: pd.DataFrame, margin: pd.DataFrame) -> dict[str, Any]:
    foreign_5d = float(institutional["foreign_net_lots"].sum()) if "foreign_net_lots" in institutional else 0.0
    investment_5d = float(institutional["investment_trust_net_lots"].sum()) if "investment_trust_net_lots" in institutional else 0.0
    dealer_5d = float(institutional["dealer_net_lots"].sum()) if "dealer_net_lots" in institutional else 0.0

    margin_change = 0.0
    margin_change_pct = 0.0
    margin_trend = "持平"
    if not margin.empty and "margin_balance" in margin.columns:
        balances = pd.to_numeric(margin["margin_balance"], errors="coerce").dropna()
        if len(balances) >= 2:
            margin_change = float(balances.iloc[-1] - balances.iloc[0])
            margin_change_pct = float(margin_change / balances.iloc[0] * 100) if balances.iloc[0] else 0.0
            margin_trend = "增加" if margin_change > 0 else "減少" if margin_change < 0 else "持平"

    return {
        "foreign_5d_lots": round(foreign_5d, 2),
        "investment_trust_5d_lots": round(investment_5d, 2),
        "dealer_5d_lots": round(dealer_5d, 2),
        "margin_change_lots": round(margin_change, 2),
        "margin_change_pct": round(margin_change_pct, 2),
        "margin_trend": margin_trend,
    }


def _fetch_twse_institutional_one_day(code: str, current: date) -> dict[str, Any] | None:
    ymd = current.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={ymd}&selectType=ALLBUT0999&response=json"
    try:
        fields, rows = parse_twse_rwd_table(fetch_text(url))
    except Exception:
        return None
    for row in rows:
        record = dict(zip(fields, row, strict=False))
        if str(record.get("證券代號", "")).strip() == code:
            foreign = _to_float(record.get("外陸資買賣超股數(不含外資自營商)"))
            investment = _to_float(record.get("投信買賣超股數"))
            dealer = _to_float(record.get("自營商買賣超股數"))
            total = _to_float(record.get("三大法人買賣超股數"))
            return _institutional_record(current, foreign, investment, dealer, total, "TWSE_T86")
    return None


def _fetch_tpex_institutional_one_day(code: str, current: date) -> dict[str, Any] | None:
    slash_date = current.strftime("%Y/%m/%d")
    url = f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?date={slash_date}&type=Daily&response=json"
    try:
        _fields, rows = parse_tpex_table(fetch_text(url))
    except Exception:
        return None
    for row in rows:
        if len(row) > 0 and str(row[0]).strip() == code:
            foreign = _to_float(row[10] if len(row) > 10 else 0)
            investment = _to_float(row[13] if len(row) > 13 else 0)
            dealer = _to_float(row[22] if len(row) > 22 else 0)
            total = _to_float(row[23] if len(row) > 23 else foreign + investment + dealer)
            return _institutional_record(current, foreign, investment, dealer, total, "TPEX_DAILY_TRADE")
    return None


def _fetch_twse_margin_one_day(code: str, current: date) -> dict[str, Any] | None:
    ymd = current.strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={ymd}&selectType=ALL&response=json"
    try:
        text = fetch_text(url)
        records = _parse_twse_margin_records(text)
    except Exception:
        return None
    for record in records:
        if str(record.get("股票代號") or record.get("證券代號") or "").strip() == code:
            return _margin_record(
                current,
                margin_buy=_to_float(record.get("融資買進")),
                margin_sell=_to_float(record.get("融資賣出")),
                margin_balance=_to_float(record.get("融資今日餘額")),
                short_sell=_to_float(record.get("融券賣出")),
                short_balance=_to_float(record.get("融券今日餘額")),
                source="TWSE_MI_MARGN_DATED",
            )
    return None


def _fetch_twse_margin_latest(code: str) -> dict[str, Any] | None:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    try:
        records = parse_json_list(fetch_text(url))
    except Exception:
        return None
    for record in records:
        if str(record.get("股票代號") or record.get("證券代號") or "").strip() == code:
            return _margin_record(
                date.today(),
                margin_buy=_to_float(record.get("融資買進")),
                margin_sell=_to_float(record.get("融資賣出")),
                margin_balance=_to_float(record.get("融資今日餘額")),
                short_sell=_to_float(record.get("融券賣出")),
                short_balance=_to_float(record.get("融券今日餘額")),
                source="TWSE_MI_MARGN_LATEST",
            )
    return None


def _fetch_tpex_margin_one_day(code: str, current: date) -> dict[str, Any] | None:
    slash_date = current.strftime("%Y/%m/%d")
    url = f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={slash_date}&response=json"
    try:
        fields, rows = parse_tpex_table(fetch_text(url))
    except Exception:
        return None
    for row in rows:
        record = dict(zip(fields, row, strict=False))
        if str(record.get("代號", "")).strip() == code:
            return _margin_record(
                current,
                margin_buy=_to_float(record.get("資買")),
                margin_sell=_to_float(record.get("資賣")),
                margin_balance=_to_float(record.get("資餘額")),
                short_sell=_to_float(record.get("券賣")),
                short_balance=_to_float(record.get("券餘額")),
                source="TPEX_MARGIN",
            )
    return None


def _parse_twse_margin_records(text: str) -> list[dict[str, Any]]:
    try:
        return parse_json_list(text)
    except Exception:
        fields, rows = parse_twse_rwd_table(text)
        return [dict(zip(fields, row, strict=False)) for row in rows]


def _institutional_record(
    current: date,
    foreign: float,
    investment: float,
    dealer: float,
    total: float,
    source: str,
) -> dict[str, Any]:
    return {
        "date": current.strftime("%Y-%m-%d"),
        "foreign_net_shares": foreign,
        "investment_trust_net_shares": investment,
        "dealer_net_shares": dealer,
        "total_institutional_net_shares": total,
        "foreign_net_lots": foreign / 1000,
        "investment_trust_net_lots": investment / 1000,
        "dealer_net_lots": dealer / 1000,
        "total_institutional_net_lots": total / 1000,
        "source": source,
    }


def _margin_record(
    current: date,
    margin_buy: float,
    margin_sell: float,
    margin_balance: float,
    short_sell: float,
    short_balance: float,
    source: str,
) -> dict[str, Any]:
    return {
        "date": current.strftime("%Y-%m-%d"),
        "margin_buy": margin_buy,
        "margin_sell": margin_sell,
        "margin_balance": margin_balance,
        "short_sell": short_sell,
        "short_balance": short_balance,
        "source": source,
    }


def _rows_to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def recent_trading_dates(limit: int) -> list[date]:
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
    text = str(value).strip().replace(",", "").replace("--", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _latest_numeric(df: Any, column: str) -> float:
    if not isinstance(df, pd.DataFrame) or df.empty or column not in df.columns:
        return 0.0
    value = pd.to_numeric(df[column], errors="coerce").dropna()
    if value.empty:
        return 0.0
    return float(value.iloc[-1])


def _latest_snapshot_date(*values: Any) -> str:
    dates: list[str] = []
    for value in values:
        if isinstance(value, pd.DataFrame) and not value.empty and "date" in value.columns:
            series = value["date"].dropna().astype(str)
            dates.extend(item[:10] for item in series if item)
        elif isinstance(value, dict) and value.get("date"):
            dates.append(str(value["date"])[:10])
    return max(dates) if dates else date.today().strftime("%Y-%m-%d")


def _status_dict(status: Any) -> dict[str, Any]:
    if status is None:
        return {}
    return {
        "source_id": getattr(status, "source_id", ""),
        "status": getattr(status, "status", "unknown"),
        "reason": getattr(status, "reason", ""),
        "last_success_at": getattr(status, "last_success_at", None),
    }


def _safe_major_holder_snapshot(ticker: str) -> dict[str, Any]:
    from src.data.major_holder_fetcher import fetch_major_holder_snapshot

    try:
        return fetch_major_holder_snapshot(ticker)
    except Exception as exc:
        return {"supported": False, "ticker": ticker, "message": str(exc)}


def _safe_health_source_id(snapshot: dict[str, Any]) -> str:
    source = snapshot.get("source")
    if isinstance(source, str) and source:
        return source
    return "major_holder_qfiis"


def _safe_source_status(source_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    message = str(snapshot.get("message") or "")
    supported = snapshot.get("supported")
    status = "ok" if supported and snapshot.get("foreign_holding_pct") is not None else "unavailable"
    if supported is False:
        status = "unsupported"
    return {
        "source_id": source_id,
        "status": status,
        "reason": message,
    }


def _should_cache_chip_snapshot(snapshot: dict[str, Any]) -> bool:
    statuses = snapshot.get("source_statuses")
    if not isinstance(statuses, dict):
        return False
    for status in statuses.values():
        if not isinstance(status, dict):
            return False
        if status.get("status") == "unavailable":
            return False
    return True
