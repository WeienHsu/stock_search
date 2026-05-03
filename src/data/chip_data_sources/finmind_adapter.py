from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import pandas as pd

from src.data.chip_data_sources.base import ChipResult, SourceStatus
from src.data.chip_utils import is_taiwan_ticker, ticker_code
from src.data.data_source_probe import fetch_text
from src.repositories.source_health_repo import record_source_health

_BASE_URL = "https://api.finmindtrade.com/api/v4/data"


class FinMindChipDataSource:
    source_id = "chip_finmind"

    def fetch_institutional_history(self, ticker: str, days: int) -> ChipResult:
        if not is_taiwan_ticker(ticker):
            return self._unsupported("僅支援台股")
        code = ticker_code(ticker)
        start_date = (date.today() - timedelta(days=days * 3 + 8)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        try:
            rows = self._fetch_rows("TaiwanStockInstitutionalInvestorsBuySell", code, start_date, end_date)
            df = self._institutional_frame(rows)
            if df.empty:
                return self._unavailable("FinMind institutional data unavailable")
            health = record_source_health(self.source_id, "ok")
            return ChipResult(df, self._status("ok", "", health.get("last_success_at")))
        except Exception as exc:
            health = record_source_health(self.source_id, "unavailable", reason=str(exc))
            return ChipResult(pd.DataFrame(), self._status("unavailable", str(exc), health.get("last_success_at")))

    def fetch_margin_history(self, ticker: str, days: int) -> ChipResult:
        if not is_taiwan_ticker(ticker):
            return self._unsupported("僅支援台股")
        code = ticker_code(ticker)
        start_date = (date.today() - timedelta(days=days * 3 + 12)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        try:
            rows = self._fetch_rows("TaiwanStockMarginPurchaseShortSale", code, start_date, end_date)
            df = self._margin_frame(rows)
            if df.empty:
                return self._unavailable("FinMind margin data unavailable")
            health = record_source_health(self.source_id, "ok")
            return ChipResult(df, self._status("ok", "", health.get("last_success_at")))
        except Exception as exc:
            health = record_source_health(self.source_id, "unavailable", reason=str(exc))
            return ChipResult(pd.DataFrame(), self._status("unavailable", str(exc), health.get("last_success_at")))

    def fetch_shareholding_snapshot(self, ticker: str) -> ChipResult:
        if not is_taiwan_ticker(ticker):
            return self._unsupported("僅支援台股")
        code = ticker_code(ticker)
        start_date = (date.today() - timedelta(days=45)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        try:
            rows = self._fetch_rows("TaiwanStockShareholding", code, start_date, end_date)
            snapshot = self._shareholding_snapshot(rows)
            if not snapshot:
                return self._unavailable("FinMind shareholding data unavailable")
            health = record_source_health(self.source_id, "ok")
            return ChipResult(snapshot, self._status("ok", "", health.get("last_success_at")))
        except Exception as exc:
            health = record_source_health(self.source_id, "unavailable", reason=str(exc))
            return ChipResult({}, self._status("unavailable", str(exc), health.get("last_success_at")))

    def fetch_monthly_revenue(self, ticker: str, months: int) -> ChipResult:
        if not is_taiwan_ticker(ticker):
            return self._unsupported("僅支援台股")
        code = ticker_code(ticker)
        start_date = (date.today() - timedelta(days=months * 40 + 60)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        try:
            rows = self._fetch_rows("TaiwanStockMonthRevenue", code, start_date, end_date)
            df = self._monthly_revenue_frame(rows)
            if df.empty:
                return self._unavailable("FinMind month revenue data unavailable")
            health = record_source_health("revenue_finmind", "ok")
            return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="revenue_finmind"))
        except Exception as exc:
            health = record_source_health("revenue_finmind", "unavailable", reason=str(exc))
            return ChipResult(pd.DataFrame(), self._status("unavailable", str(exc), health.get("last_success_at"), source_id="revenue_finmind"))

    def fetch_total_institutional(self, days: int) -> ChipResult:
        start_date = (date.today() - timedelta(days=days * 3 + 8)).strftime("%Y-%m-%d")
        end_date = date.today().strftime("%Y-%m-%d")
        try:
            rows = self._fetch_rows("TaiwanStockTotalInstitutionalInvestors", "", start_date, end_date)
            df = pd.DataFrame(rows)
            if df.empty:
                return self._unavailable("FinMind total institutional data unavailable")
            health = record_source_health("chip_finmind_total", "ok")
            return ChipResult(df, self._status("ok", "", health.get("last_success_at"), source_id="chip_finmind_total"))
        except Exception as exc:
            health = record_source_health("chip_finmind_total", "unavailable", reason=str(exc))
            return ChipResult(pd.DataFrame(), self._status("unavailable", str(exc), health.get("last_success_at"), source_id="chip_finmind_total"))

    def _fetch_rows(self, dataset: str, code: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
        params = {
            "dataset": dataset,
            "start_date": start_date,
            "end_date": end_date,
        }
        if code:
            params["data_id"] = code
        token = os.getenv("FINMIND_API_TOKEN", "").strip()
        if token:
            params["token"] = token
        payload = json.loads(fetch_text(f"{_BASE_URL}?{urlencode(params)}"))
        if payload.get("status") != 200:
            raise ValueError(f"FinMind status={payload.get('status')}, msg={payload.get('msg')}")
        rows = payload.get("data") or []
        if not isinstance(rows, list):
            raise ValueError("FinMind data is not a list")
        return [row for row in rows if isinstance(row, dict)]

    def _institutional_frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        by_date: dict[str, dict[str, Any]] = {}
        for row in rows:
            row_date = str(row.get("date") or "").strip()
            if not row_date:
                continue
            bucket = by_date.setdefault(row_date, {
                "date": row_date,
                "foreign_net_shares": 0.0,
                "investment_trust_net_shares": 0.0,
                "dealer_net_shares": 0.0,
                "total_institutional_net_shares": 0.0,
                "source": "FinMind",
            })
            name = str(row.get("name") or row.get("type") or "").strip()
            buy = _to_float(row.get("buy"))
            sell = _to_float(row.get("sell"))
            net = buy - sell
            investor_type = _investor_type(name)
            if investor_type == "foreign":
                bucket["foreign_net_shares"] += net
            elif investor_type == "investment_trust":
                bucket["investment_trust_net_shares"] += net
            elif investor_type == "dealer":
                bucket["dealer_net_shares"] += net
            if "三大法人" in name or "總和" in name or "total" in name.lower():
                bucket["total_institutional_net_shares"] = net
        for bucket in by_date.values():
            if not bucket["total_institutional_net_shares"]:
                bucket["total_institutional_net_shares"] = (
                    bucket["foreign_net_shares"]
                    + bucket["investment_trust_net_shares"]
                    + bucket["dealer_net_shares"]
                )
            bucket["foreign_net_lots"] = bucket["foreign_net_shares"] / 1000
            bucket["investment_trust_net_lots"] = bucket["investment_trust_net_shares"] / 1000
            bucket["dealer_net_lots"] = bucket["dealer_net_shares"] / 1000
            bucket["total_institutional_net_lots"] = bucket["total_institutional_net_shares"] / 1000
        return pd.DataFrame(sorted(by_date.values(), key=lambda item: item["date"]))

    def _margin_frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        records = []
        for row in rows:
            row_date = str(row.get("date") or "").strip()
            if not row_date:
                continue
            records.append({
                "date": row_date,
                "margin_buy": _to_float(row.get("MarginPurchaseBuy")),
                "margin_sell": _to_float(row.get("MarginPurchaseSell")),
                "margin_balance": _to_float(row.get("MarginPurchaseTodayBalance")),
                "short_sell": _to_float(row.get("ShortSaleSell")),
                "short_balance": _to_float(row.get("ShortSaleTodayBalance")),
                "source": "FinMind",
            })
        return pd.DataFrame(records).sort_values("date").reset_index(drop=True) if records else pd.DataFrame()

    def _shareholding_snapshot(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {}
        latest = max(rows, key=lambda row: str(row.get("date") or ""))
        pct = _to_float(
            latest.get("ForeignInvestmentSharesRatio")
            or latest.get("ForeignInvestmentRemainRatio")
            or latest.get("foreign_holding_pct")
        )
        return {
            "supported": True,
            "ticker": ticker_code(str(latest.get("stock_id") or latest.get("ticker") or "")),
            "code": ticker_code(str(latest.get("stock_id") or latest.get("ticker") or "")),
            "date": str(latest.get("date") or ""),
            "foreign_holding_pct": pct,
            "source": "FinMind",
        }

    def _monthly_revenue_frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        records = []
        for row in rows:
            row_date = str(row.get("date") or row.get("revenue_month") or "").strip()
            if not row_date:
                continue
            period = row_date[:7] if len(row_date) >= 7 else row_date
            records.append({
                "period": period,
                "revenue": _to_float(row.get("revenue")),
                "yoy_pct": _to_float_or_none(row.get("yoy_pct") or row.get("YoY") or row.get("growth")),
                "source": "revenue_finmind",
            })
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records).sort_values("period").reset_index(drop=True)
        return _fill_monthly_revenue_yoy(df)

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

    def _unsupported(self, reason: str) -> ChipResult:
        health = record_source_health(self.source_id, "unsupported", reason=reason)
        return ChipResult(
            pd.DataFrame() if "month" not in reason.lower() else pd.DataFrame(),
            self._status("unsupported", reason, health.get("last_success_at")),
        )

    def _unavailable(self, reason: str) -> ChipResult:
        health = record_source_health(self.source_id, "unavailable", reason=reason)
        return ChipResult(pd.DataFrame(), self._status("unavailable", reason, health.get("last_success_at")))


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


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _fill_monthly_revenue_yoy(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "period" not in df.columns or "revenue" not in df.columns:
        return df
    result = df.copy()
    revenue_by_period = {
        str(row["period"]): float(row["revenue"])
        for _, row in result.iterrows()
        if pd.notna(row.get("revenue"))
    }
    yoy_values = []
    for _, row in result.iterrows():
        current_yoy = row.get("yoy_pct")
        if pd.notna(current_yoy):
            yoy_values.append(float(current_yoy))
            continue
        period = str(row.get("period") or "")
        try:
            year_text, month_text = period.split("-", 1)
            previous_period = f"{int(year_text) - 1:04d}-{int(month_text):02d}"
        except (TypeError, ValueError):
            yoy_values.append(pd.NA)
            continue
        previous_revenue = revenue_by_period.get(previous_period)
        current_revenue = row.get("revenue")
        if previous_revenue and pd.notna(current_revenue):
            yoy_values.append((float(current_revenue) / previous_revenue - 1) * 100)
        else:
            yoy_values.append(pd.NA)
    result.loc[:, "yoy_pct"] = yoy_values
    return result


def _investor_type(name: str) -> str:
    normalized = name.strip().lower().replace(" ", "_")
    if not normalized:
        return ""
    if "investment_trust" in normalized or "投信" in name:
        return "investment_trust"
    if "dealer" in normalized or "自營商" in name:
        return "dealer"
    if "foreign_investor" in normalized or ("foreign" in normalized and "dealer" not in normalized) or "外資" in name:
        return "foreign"
    return ""
