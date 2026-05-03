from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import pandas as pd

from src.data.chip_data_sources.base import ChipResult, SourceStatus
from src.data.chip_utils import market_kind, ticker_code
from src.data.data_source_probe import fetch_text, parse_json_list, parse_twse_rwd_table
from src.repositories.source_health_repo import record_source_health


class TwseChipDataSource:
    source_id = "chip_twse"

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult:
        if market_kind(ticker) != "twse":
            return self._unsupported("僅支援上市台股")
        code = ticker_code(ticker)
        rows: list[dict[str, Any]] = []
        for current in self._recent_trading_dates(days * 3 + 8):
            if len(rows) >= days:
                break
            record = self._fetch_twse_institutional_one_day(code, current)
            if record:
                rows.append(record)
        if not rows:
            return self._unavailable("TWSE institutional data unavailable")
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        health = record_source_health("chip_twse_t86", "ok")
        return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="chip_twse_t86"))

    def fetch_margin_history(self, ticker: str, days: int) -> ChipResult:
        if market_kind(ticker) != "twse":
            return self._unsupported("僅支援上市台股")
        code = ticker_code(ticker)
        rows: list[dict[str, Any]] = []
        for current in self._recent_trading_dates(days * 3 + 12):
            if len(rows) >= days:
                break
            record = self._fetch_twse_margin_one_day(code, current)
            if record:
                rows.append(record)
        if not rows:
            latest = self._fetch_twse_margin_latest(code)
            if latest:
                rows.append(latest)
        if not rows:
            return self._unavailable("TWSE margin data unavailable")
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        health = record_source_health("chip_twse_margn", "ok")
        return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="chip_twse_margn"))

    def fetch_shareholding_snapshot(self, ticker: str) -> ChipResult:
        if market_kind(ticker) != "twse":
            return self._unsupported("僅支援上市台股")
        code = ticker_code(ticker)
        try:
            snapshot = self._fetch_twse_foreign_holding(code)
            if not snapshot:
                return self._unavailable("TWSE foreign holding data unavailable")
            health = record_source_health("major_holder_qfiis", "ok")
            return ChipResult(snapshot, self._status("ok", "", health.get("last_success_at"), source_id="major_holder_qfiis"))
        except Exception as exc:
            health = record_source_health("major_holder_qfiis", "unavailable", reason=str(exc))
            return ChipResult({}, self._status("unavailable", str(exc), health.get("last_success_at"), source_id="major_holder_qfiis"))

    def fetch_monthly_revenue(self, ticker: str, months: int) -> ChipResult:
        return self._unsupported("月營收不由 TWSE 直接提供")

    def fetch_total_institutional(self, days: int) -> ChipResult:
        return self._unsupported("不提供市場法人總量")

    def _fetch_twse_institutional_one_day(self, code: str, current: date) -> dict[str, Any] | None:
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

    def _fetch_twse_margin_one_day(self, code: str, current: date) -> dict[str, Any] | None:
        ymd = current.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={ymd}&selectType=ALL&response=json"
        try:
            text = fetch_text(url)
            records = _parse_twse_margin_records(text)
        except Exception:
            return None
        for record in records:
            if str(record.get("股票代號") or record.get("證券代號") or record.get("代號") or "").strip() == code:
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

    def _fetch_twse_margin_latest(self, code: str) -> dict[str, Any] | None:
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

    def _fetch_twse_foreign_holding(self, code: str) -> dict[str, Any] | None:
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
                    pct = _to_float(
                        row.get("全體外資及陸資持股比率")
                        or row.get("外資及陸資持股比率")
                        or row.get("ForeignInvestmentRemainingRatio")
                    )
                    return {
                        "supported": True,
                        "ticker": f"{code}.TW",
                        "code": code,
                        "foreign_holding_pct": pct,
                        "source": "TWSE_MI_QFIIS",
                    }
        return None

    def _recent_trading_dates(self, limit: int) -> list[date]:
        current = date.today()
        dates = []
        while len(dates) < limit:
            if current.weekday() < 5:
                dates.append(current)
            current -= timedelta(days=1)
        return dates

    def _unsupported(self, reason: str) -> ChipResult:
        health = record_source_health(self.source_id, "unsupported", reason=reason)
        return ChipResult(pd.DataFrame(), self._status("unsupported", reason, health.get("last_success_at")))

    def _unavailable(self, reason: str) -> ChipResult:
        health = record_source_health(self.source_id, "unavailable", reason=reason)
        return ChipResult(pd.DataFrame(), self._status("unavailable", reason, health.get("last_success_at")))

    def _status(
        self,
        status: str,
        reason: str,
        last_success_at: Any = None,
        *,
        source_id: str | None = None,
    ) -> SourceStatus:
        return SourceStatus(
            source_id=source_id or self.source_id,
            status=status,  # type: ignore[arg-type]
            reason=reason,
            last_success_at=last_success_at,
        )


def _parse_twse_margin_records(text: str) -> list[dict[str, Any]]:
    try:
        return parse_json_list(text)
    except Exception:
        pass
    try:
        fields, rows = parse_twse_rwd_table(text)
        return [dict(zip(fields, row, strict=False)) for row in rows]
    except Exception:
        pass
    payload = json.loads(text)
    for table in payload.get("tables") or []:
        if not isinstance(table, dict):
            continue
        rows = table.get("data") or []
        fields = table.get("fields") or []
        if rows and "代號" in fields and "名稱" in fields:
            records = []
            for row in rows:
                records.append({
                    "代號": row[0] if len(row) > 0 else "",
                    "融資買進": row[2] if len(row) > 2 else 0,
                    "融資賣出": row[3] if len(row) > 3 else 0,
                    "融資今日餘額": row[6] if len(row) > 6 else 0,
                    "融券賣出": row[9] if len(row) > 9 else 0,
                    "融券今日餘額": row[12] if len(row) > 12 else 0,
                })
            return records
    return []


def _parse_twse_qfiis_records(text: str) -> list[dict[str, Any]]:
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


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0
