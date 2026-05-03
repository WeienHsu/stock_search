from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Literal

import pandas as pd

from src.data.data_source_probe import fetch_text, parse_json_list, parse_tpex_table, parse_twse_rwd_table
from src.repositories.chip_data_cache_repo import get_chip_cache, save_chip_cache

MarketKind = Literal["twse", "tpex", "unsupported"]

_DAY = 24 * 3600


def is_taiwan_ticker(ticker: str) -> bool:
    return market_kind(ticker) != "unsupported"


def market_kind(ticker: str) -> MarketKind:
    normalized = ticker.upper()
    if normalized.endswith(".TW"):
        return "twse"
    if normalized.endswith(".TWO"):
        return "tpex"
    return "unsupported"


def fetch_chip_snapshot(ticker: str, institutional_days: int = 5, margin_days: int = 20) -> dict[str, Any]:
    kind = market_kind(ticker)
    if kind == "unsupported":
        return {"supported": False, "ticker": ticker, "market": kind}

    code = ticker_code(ticker)
    cache_key = f"chip_snapshot_v2_{kind}_{code}_{institutional_days}_{margin_days}"
    cached = get_chip_cache(cache_key, ttl_override=_DAY)
    if isinstance(cached, dict) and cached:
        return cached

    institutional = fetch_institutional_trades(ticker, institutional_days)
    margin = fetch_margin_trend(ticker, margin_days)
    summary = summarize_chip_data(institutional, margin)
    result = {
        "supported": True,
        "ticker": ticker,
        "code": code,
        "market": kind,
        "institutional": institutional,
        "margin": margin,
        "summary": summary,
    }
    save_chip_cache(cache_key, result)
    return result


def fetch_institutional_trades(ticker: str, days: int = 5) -> pd.DataFrame:
    kind = market_kind(ticker)
    code = ticker_code(ticker)
    rows: list[dict[str, Any]] = []
    for current in recent_trading_dates(days * 3 + 8):
        if len(rows) >= days:
            break
        record = _fetch_twse_institutional_one_day(code, current) if kind == "twse" else _fetch_tpex_institutional_one_day(code, current)
        if record:
            rows.append(record)
    return _rows_to_df(rows)


def fetch_margin_trend(ticker: str, days: int = 20) -> pd.DataFrame:
    kind = market_kind(ticker)
    code = ticker_code(ticker)
    rows: list[dict[str, Any]] = []
    for current in recent_trading_dates(days * 3 + 12):
        if len(rows) >= days:
            break
        record = _fetch_twse_margin_one_day(code, current) if kind == "twse" else _fetch_tpex_margin_one_day(code, current)
        if record:
            rows.append(record)
    if kind == "twse" and not rows:
        latest = _fetch_twse_margin_latest(code)
        if latest:
            rows.append(latest)
    return _rows_to_df(rows)


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


def ticker_code(ticker: str) -> str:
    return ticker.upper().split(".", 1)[0]


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
