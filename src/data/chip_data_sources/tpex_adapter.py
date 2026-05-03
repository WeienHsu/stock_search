from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from src.data.chip_data_sources.base import ChipResult, SourceStatus
from src.data.chip_utils import market_kind, ticker_code
from src.data.data_source_probe import fetch_text, parse_json_list, parse_tpex_table
from src.repositories.source_health_repo import record_source_health


class TpexChipDataSource:
    source_id = "chip_tpex"

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult:
        if market_kind(ticker) != "tpex":
            return self._unsupported("僅支援上櫃台股")
        code = ticker_code(ticker)
        rows: list[dict[str, Any]] = []
        for current in self._recent_trading_dates(days * 3 + 8):
            if len(rows) >= days:
                break
            record = self._fetch_tpex_institutional_one_day(code, current)
            if record:
                rows.append(record)
        if not rows:
            return self._unavailable("TPEX institutional data unavailable")
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        health = record_source_health("chip_tpex_daily_trade", "ok")
        return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="chip_tpex_daily_trade"))

    def fetch_margin_history(self, ticker: str, days: int) -> ChipResult:
        if market_kind(ticker) != "tpex":
            return self._unsupported("僅支援上櫃台股")
        code = ticker_code(ticker)
        rows: list[dict[str, Any]] = []
        for current in self._recent_trading_dates(days * 3 + 12):
            if len(rows) >= days:
                break
            record = self._fetch_tpex_margin_one_day(code, current)
            if record:
                rows.append(record)
        if not rows:
            return self._unavailable("TPEX margin data unavailable")
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        health = record_source_health("chip_tpex_margin", "ok")
        return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="chip_tpex_margin"))

    def fetch_shareholding_snapshot(self, ticker: str) -> ChipResult:
        if market_kind(ticker) != "tpex":
            return self._unsupported("僅支援上櫃台股")
        code = ticker_code(ticker)
        try:
            snapshot = self._fetch_tpex_foreign_holding(code)
            if not snapshot:
                return self._unavailable("TPEX foreign holding data unavailable")
            health = record_source_health("major_holder_qfiis", "ok")
            return ChipResult(snapshot, self._status("ok", "", health.get("last_success_at"), source_id="major_holder_qfiis"))
        except Exception as exc:
            health = record_source_health("major_holder_qfiis", "unavailable", reason=str(exc))
            return ChipResult({}, self._status("unavailable", str(exc), health.get("last_success_at"), source_id="major_holder_qfiis"))

    def fetch_monthly_revenue(self, ticker: str, months: int) -> ChipResult:
        return self._unsupported("月營收不由 TPEX 直接提供")

    def fetch_total_institutional(self, days: int) -> ChipResult:
        return self._unsupported("不提供市場法人總量")

    def _fetch_tpex_institutional_one_day(self, code: str, current: date) -> dict[str, Any] | None:
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

    def _fetch_tpex_margin_one_day(self, code: str, current: date) -> dict[str, Any] | None:
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

    def _fetch_tpex_foreign_holding(self, code: str) -> dict[str, Any] | None:
        urls = [
            "https://www.tpex.org.tw/openapi/v1/tpex_3insti_qfii",
            "https://www.tpex.org.tw/www/zh-tw/foreign/forgHold?response=json",
        ]
        for url in urls:
            try:
                text = fetch_text(url)
                if url.endswith("tpex_3insti_qfii"):
                    records = parse_json_list(text)
                    for row in records:
                        row_code = str(row.get("SecuritiesCompanyCode") or "").strip()
                        if row_code == code:
                            pct = _to_float(row.get("PercentageOfSharesOC/FMIHeld"))
                            return {
                                "supported": True,
                                "ticker": f"{code}.TWO",
                                "code": code,
                                "foreign_holding_pct": pct,
                                "source": "TPEX_OPENAPI_QFII",
                            }
                else:
                    fields, rows = parse_tpex_table(text)
                    for row in rows:
                        record = dict(zip(fields, row, strict=False))
                        row_code = str(record.get("代號") or "").strip()
                        if row_code == code:
                            pct = _to_float(record.get("外資持股比率") or record.get("外資及陸資持股比率"))
                            return {
                                "supported": True,
                                "ticker": f"{code}.TWO",
                                "code": code,
                                "foreign_holding_pct": pct,
                                "source": "TPEX_FOREIGN_HOLDING",
                            }
            except Exception:
                continue
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
