from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - script still works without python-dotenv
    load_dotenv = None

from src.data.data_source_probe import (
    fetch_text,
    parse_json_list,
    parse_tpex_table,
    parse_twse_rwd_table,
)

if load_dotenv:
    load_dotenv()


DEFAULT_TICKER = "2330"
DEFAULT_DATE = "20260430"
DEFAULT_START_DATE = "2026-04-01"
DEFAULT_END_DATE = "2026-04-30"


@dataclass
class ChipSourceProbeResult:
    name: str
    status: str
    source_url: str
    records_count: int
    sample: dict[str, Any]
    mapping: dict[str, str]
    role: str
    rate_limit: str
    failure_modes: list[str]
    recommendation: str
    notes: list[str]


def run_all_probes(
    ticker: str = DEFAULT_TICKER,
    probe_date: str = DEFAULT_DATE,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
) -> list[ChipSourceProbeResult]:
    ymd = _yyyymmdd(probe_date)
    slash_date = f"{ymd[:4]}/{ymd[4:6]}/{ymd[6:]}"
    iso_date = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"

    return [
        _probe_finmind_institutional(ticker, start_date, end_date),
        _probe_finmind_margin(ticker, start_date, end_date),
        _probe_finmind_shareholding(ticker, start_date, end_date),
        _probe_finmind_month_revenue(ticker, start_date, end_date),
        _probe_finmind_total_institutional(start_date, end_date),
        _probe_twse_t86(ymd),
        _probe_twse_margin_openapi(),
        _probe_twse_margin_rwd(ymd),
        _probe_twse_qfiis_openapi_top20(),
        _probe_twse_qfiis_openapi_industry(),
        _probe_twse_qfiis_legacy_full(),
        _probe_twse_realtime_breadth(),
        _probe_tpex_institutional_openapi(),
        _probe_tpex_institutional_rwd(slash_date),
        _probe_tpex_margin_openapi(),
        _probe_tpex_margin_rwd(slash_date),
        _probe_tpex_qfii_openapi(),
        _probe_tpex_qfii_trading_openapi(),
        _probe_mops_month_revenue(ticker, iso_date),
        _probe_datagov_twse_qfiis_metadata(),
        _probe_datagov_tpex_institutional_metadata(),
        _probe_datagov_tpex_margin_metadata(),
    ]


def write_artifacts(
    results: list[ChipSourceProbeResult],
    markdown_path: str = "docs/data_source_mapping_20260503.md",
    json_path: str = "docs/data_source_mapping_20260503.json",
) -> None:
    Path(markdown_path).write_text(render_markdown(results), encoding="utf-8")
    Path(json_path).write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_markdown(results: list[ChipSourceProbeResult]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Data Source Mapping 2026-05-03",
        "",
        f"Generated at: {generated_at}",
        "",
        "## A0 結論",
        "",
        "- FinMind v4 對本期需要的歷史法人、融資融券、外資持股、月營收、全市場法人動向皆可回傳歷史資料；A1 可把 FinMind 設為主源。",
        "- TWSE / TPEX OpenAPI 適合作為 latest snapshot 或 fallback；RWD JSON 可作 dated fallback，但假日或無交易日時要往前找交易日。",
        "- TWSE RWD `MI_MARGN` dated endpoint 回傳巢狀 `tables`，不是單層 `fields/data`；A1/A2 若保留此 fallback，需要專用 parser。",
        "- data.gov.tw 本次確認主要是 metadata / OAS 入口，不是較穩定的直接資料 API；實作應直接打 TWSE / TPEX OpenAPI。",
        "- TWSE `MI_QFIIS` 個股完整外資持股 endpoint 目前不穩定或不存在；上市個股 `qfiis_pct` 建議優先使用 FinMind `TaiwanStockShareholding`。",
        "- TWSE 即時委買委賣 `MI_5MINS` 可用，但欄位是 `AccBidVolume` / `AccAskVolume`，現有 parser 若只找舊欄名會落入 unavailable。",
        "",
        "## Summary",
        "",
        "| Source | Status | Records | Role | Recommendation |",
        "|--------|--------|---------|------|----------------|",
    ]
    for result in results:
        lines.append(
            f"| {result.name} | {result.status} | {result.records_count} | {result.role} | {result.recommendation} |"
        )

    lines.extend(["", "## Details", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- URL: `{_redact_url(result.source_url)}`",
                f"- Status: `{result.status}`",
                f"- Records: `{result.records_count}`",
                f"- Role: {result.role}",
                f"- Rate limit / update cadence: {result.rate_limit}",
                f"- Recommendation: {result.recommendation}",
                "",
                "Failure modes:",
            ]
        )
        for failure in result.failure_modes:
            lines.append(f"- {failure}")
        lines.extend(["", "Notes:"])
        for note in result.notes:
            lines.append(f"- {note}")
        lines.extend(["", "| Canonical Field | Source Field |", "|-----------------|--------------|"])
        for canonical, source in result.mapping.items():
            lines.append(f"| `{canonical}` | `{source}` |")
        lines.extend(["", "Sample:", "", "```json"])
        lines.append(json.dumps(result.sample, ensure_ascii=False, indent=2))
        lines.extend(["```", ""])

    return "\n".join(lines)


def _probe_finmind_institutional(ticker: str, start_date: str, end_date: str) -> ChipSourceProbeResult:
    dataset = "TaiwanStockInstitutionalInvestorsBuySell"
    url = _finmind_url(dataset, ticker, start_date, end_date)
    return _guarded(
        "FINMIND_INSTITUTIONAL_INVESTORS_BUY_SELL",
        url,
        lambda: _finmind_result(
            name="FINMIND_INSTITUTIONAL_INVESTORS_BUY_SELL",
            url=url,
            mapping={
                "date": "date",
                "ticker": "stock_id",
                "investor_type": "name",
                "buy_shares": "buy",
                "sell_shares": "sell",
                "net_shares": "buy - sell",
            },
            role="primary",
            rate_limit=_finmind_rate_limit_note(),
            failure_modes=[
                "Tokenless usage may be throttled; production should set FINMIND_API_TOKEN.",
                "Rows are one investor type per date, so adapter must pivot/aggregate before UI use.",
            ],
            recommendation="Use as primary historical institutional flow source.",
            notes=["Covers historical per-stock institutional buy/sell rows."],
        ),
    )


def _probe_finmind_margin(ticker: str, start_date: str, end_date: str) -> ChipSourceProbeResult:
    dataset = "TaiwanStockMarginPurchaseShortSale"
    url = _finmind_url(dataset, ticker, start_date, end_date)
    return _guarded(
        "FINMIND_MARGIN_PURCHASE_SHORT_SALE",
        url,
        lambda: _finmind_result(
            name="FINMIND_MARGIN_PURCHASE_SHORT_SALE",
            url=url,
            mapping={
                "date": "date",
                "ticker": "stock_id",
                "margin_buy": "MarginPurchaseBuy",
                "margin_sell": "MarginPurchaseSell",
                "margin_balance": "MarginPurchaseTodayBalance",
                "short_sell": "ShortSaleSell",
                "short_balance": "ShortSaleTodayBalance",
            },
            role="primary",
            rate_limit=_finmind_rate_limit_note(),
            failure_modes=["Tokenless usage may be throttled; production should set FINMIND_API_TOKEN."],
            recommendation="Use as primary historical margin/short source.",
            notes=["Returns dated history, so it fixes fake 20-day trend risk when persisted as snapshots."],
        ),
    )


def _probe_finmind_shareholding(ticker: str, start_date: str, end_date: str) -> ChipSourceProbeResult:
    dataset = "TaiwanStockShareholding"
    url = _finmind_url(dataset, ticker, start_date, end_date)
    return _guarded(
        "FINMIND_SHAREHOLDING",
        url,
        lambda: _finmind_result(
            name="FINMIND_SHAREHOLDING",
            url=url,
            mapping={
                "date": "date",
                "ticker": "stock_id",
                "name": "stock_name",
                "foreign_holding_pct": "ForeignInvestmentSharesRatio",
                "foreign_remaining_pct": "ForeignInvestmentRemainRatio",
                "shares_issued": "NumberOfSharesIssued",
            },
            role="primary",
            rate_limit=_finmind_rate_limit_note(),
            failure_modes=["Tokenless usage may be throttled; production should set FINMIND_API_TOKEN."],
            recommendation="Use as primary qfiis_pct source for listed stocks.",
            notes=["Current TWSE OpenAPI exposes top20/industry QFIIS, not full per-stock lookup."],
        ),
    )


def _probe_finmind_month_revenue(ticker: str, start_date: str, end_date: str) -> ChipSourceProbeResult:
    dataset = "TaiwanStockMonthRevenue"
    url = _finmind_url(dataset, ticker, start_date, end_date)
    return _guarded(
        "FINMIND_MONTH_REVENUE",
        url,
        lambda: _finmind_result(
            name="FINMIND_MONTH_REVENUE",
            url=url,
            mapping={
                "date": "date",
                "ticker": "stock_id",
                "revenue": "revenue",
                "revenue_month": "revenue_month",
                "revenue_year": "revenue_year",
                "created_at": "create_time",
            },
            role="primary",
            rate_limit=_finmind_rate_limit_note(),
            failure_modes=[
                "Monthly data may appear after issuer filing, not on every trading day.",
                "Tokenless usage may be throttled; production should set FINMIND_API_TOKEN.",
            ],
            recommendation="Use as primary monthly revenue source; keep MOPS parser as fallback.",
            notes=["Historical monthly revenue is easier to consume here than HTML MOPS scraping."],
        ),
    )


def _probe_finmind_total_institutional(start_date: str, end_date: str) -> ChipSourceProbeResult:
    dataset = "TaiwanStockTotalInstitutionalInvestors"
    url = _finmind_url(dataset, "", start_date, end_date)
    return _guarded(
        "FINMIND_TOTAL_INSTITUTIONAL_INVESTORS",
        url,
        lambda: _finmind_result(
            name="FINMIND_TOTAL_INSTITUTIONAL_INVESTORS",
            url=url,
            mapping={
                "date": "date",
                "investor_type": "name",
                "market_buy_amount": "buy",
                "market_sell_amount": "sell",
                "market_net_amount": "buy - sell",
            },
            role="primary",
            rate_limit=_finmind_rate_limit_note(),
            failure_modes=["Tokenless usage may be throttled; production should set FINMIND_API_TOKEN."],
            recommendation="Use for market overview institutional totals.",
            notes=["Rows are by investor type per date, including total."],
        ),
    )


def _probe_twse_t86(date: str) -> ChipSourceProbeResult:
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date}&selectType=ALLBUT0999&response=json"
    return _guarded(
        "TWSE_RWD_T86_LISTED_INSTITUTIONAL",
        url,
        lambda: _twse_rwd_result(
            name="TWSE_RWD_T86_LISTED_INSTITUTIONAL",
            url=url,
            mapping={
                "ticker": "證券代號",
                "name": "證券名稱",
                "foreign_net_shares": "外陸資買賣超股數(不含外資自營商)",
                "investment_trust_net_shares": "投信買賣超股數",
                "dealer_net_shares": "自營商買賣超股數",
                "total_institutional_net_shares": "三大法人買賣超股數",
            },
            role="fallback",
            rate_limit="Daily TWSE RWD endpoint; no documented app quota in response.",
            failure_modes=["Date-sensitive; holiday/current-day requests often return no rows.", "ETF category may require selectType handling."],
            recommendation="Keep as listed-stock fallback when FinMind is unavailable.",
            notes=["Works for listed stocks and returns a full market table for the requested date."],
        ),
    )


def _probe_twse_margin_openapi() -> ChipSourceProbeResult:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    return _guarded(
        "TWSE_OPENAPI_MI_MARGN_LATEST",
        url,
        lambda: _json_list_result(
            name="TWSE_OPENAPI_MI_MARGN_LATEST",
            url=url,
            mapping={
                "ticker": "股票代號",
                "name": "股票名稱",
                "margin_buy": "融資買進",
                "margin_sell": "融資賣出",
                "margin_balance": "融資今日餘額",
                "short_sell": "融券賣出",
                "short_balance": "融券今日餘額",
            },
            role="fallback",
            rate_limit="Latest daily OpenAPI snapshot; data.gov marks related datasets as daily.",
            failure_modes=["Only latest snapshot; not enough alone for historical trend reconstruction."],
            recommendation="Use as latest fallback and for scheduler daily snapshot.",
            notes=["Direct JSON list is stable and easy to parse."],
        ),
    )


def _probe_twse_margin_rwd(date: str) -> ChipSourceProbeResult:
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date}&selectType=ALL&response=json"
    return _guarded(
        "TWSE_RWD_MI_MARGN_DATED",
        url,
        lambda: _twse_margin_rwd_result(
            name="TWSE_RWD_MI_MARGN_DATED",
            url=url,
            mapping={
                "ticker": "tables[1].data[0] 代號",
                "name": "tables[1].data[1] 名稱",
                "margin_buy": "tables[1].data[2] 融資買進",
                "margin_sell": "tables[1].data[3] 融資賣出",
                "margin_balance": "tables[1].data[6] 融資今日餘額",
                "short_sell": "tables[1].data[9] 融券賣出",
                "short_balance": "tables[1].data[12] 融券今日餘額",
            },
            role="fallback",
            rate_limit="Daily TWSE RWD endpoint; no documented app quota in response.",
            failure_modes=[
                "Date-sensitive; current-day or holiday requests may fail.",
                "Nested tables format requires selecting the detail table before mapping fields.",
            ],
            recommendation="Keep as dated fallback only; prefer FinMind for historical range.",
            notes=["Useful when daily scheduler needs an explicit date.", "Existing generic TWSE RWD parser is not enough for this endpoint."],
        ),
    )


def _probe_twse_qfiis_openapi_top20() -> ChipSourceProbeResult:
    url = "https://openapi.twse.com.tw/v1/fund/MI_QFIIS_sort_20"
    return _guarded(
        "TWSE_OPENAPI_MI_QFIIS_TOP20",
        url,
        lambda: _json_list_result(
            name="TWSE_OPENAPI_MI_QFIIS_TOP20",
            url=url,
            mapping={
                "rank": "Rank",
                "ticker": "Code",
                "name": "Name",
                "foreign_holding_pct": "SharesHeldPer",
                "available_invest_pct": "AvailableInvestPer",
            },
            role="diagnostic",
            rate_limit="Latest daily OpenAPI snapshot.",
            failure_modes=["Top 20 only; cannot power arbitrary ticker lookup."],
            recommendation="Do not use as qfiis_pct source for Dashboard ticker lookup.",
            notes=["Useful only as market overview diagnostic/top list."],
        ),
    )


def _probe_twse_qfiis_openapi_industry() -> ChipSourceProbeResult:
    url = "https://openapi.twse.com.tw/v1/fund/MI_QFIIS_cat"
    return _guarded(
        "TWSE_OPENAPI_MI_QFIIS_INDUSTRY",
        url,
        lambda: _json_list_result(
            name="TWSE_OPENAPI_MI_QFIIS_INDUSTRY",
            url=url,
            mapping={
                "industry": "IndustryCat",
                "listed_count": "Numbers",
                "shares_issued": "ShareNumber",
                "foreign_holding_shares": "ForeignMainlandAreaShare",
                "foreign_holding_pct": "Percentage",
            },
            role="diagnostic",
            rate_limit="Latest daily OpenAPI snapshot.",
            failure_modes=["Industry aggregate only; cannot power arbitrary ticker lookup."],
            recommendation="Use only for market overview if needed.",
            notes=["data.gov dataset 11655 points to this kind of TWSE OAS/OpenAPI metadata."],
        ),
    )


def _probe_twse_qfiis_legacy_full() -> ChipSourceProbeResult:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_QFIIS"
    return _guarded(
        "TWSE_OPENAPI_MI_QFIIS_LEGACY_FULL_LOOKUP",
        url,
        lambda: _json_list_result(
            name="TWSE_OPENAPI_MI_QFIIS_LEGACY_FULL_LOOKUP",
            url=url,
            mapping={
                "ticker": "股票代號 / 證券代號",
                "foreign_holding_pct": "外資及陸資持股比率",
            },
            role="not_recommended",
            rate_limit="Unknown; endpoint is not present in current TWSE swagger path list.",
            failure_modes=["Likely 404 or empty; current code should not depend on it as primary."],
            recommendation="Replace with FinMind shareholding or documented TWSE paths.",
            notes=["This checks the legacy endpoint currently referenced by major_holder_fetcher."],
        ),
    )


def _probe_twse_realtime_breadth() -> ChipSourceProbeResult:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_5MINS"
    return _guarded(
        "TWSE_OPENAPI_MI_5MINS_REALTIME_BREADTH",
        url,
        lambda: _json_list_result(
            name="TWSE_OPENAPI_MI_5MINS_REALTIME_BREADTH",
            url=url,
            mapping={
                "time": "Time",
                "buy_orders": "AccBidOrders",
                "buy_volume_lots": "AccBidVolume",
                "sell_orders": "AccAskOrders",
                "sell_volume_lots": "AccAskVolume",
                "trade_volume_lots": "AccTradeVolume",
                "trade_value": "AccTradeValue",
            },
            role="fallback",
            rate_limit="Intraday OpenAPI snapshot; cache aggressively during market hours.",
            failure_modes=["Unavailable outside source update windows; parser must use AccBidVolume/AccAskVolume names."],
            recommendation="Use for realtime breadth, but fix parser field aliases before relying on UI health.",
            notes=["This covers L8 realtime bid/ask breadth mapping."],
        ),
    )


def _probe_tpex_institutional_openapi() -> ChipSourceProbeResult:
    url = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"
    return _guarded(
        "TPEX_OPENAPI_3INSTI_DAILY_TRADING",
        url,
        lambda: _json_list_result(
            name="TPEX_OPENAPI_3INSTI_DAILY_TRADING",
            url=url,
            mapping={
                "date": "Date",
                "ticker": "SecuritiesCompanyCode",
                "name": "CompanyName",
                "foreign_net_shares": "ForeignInvestorsInclude MainlandAreaInvestors-Difference",
                "investment_trust_net_shares": "SecuritiesInvestmentTrustCompanies-Difference",
                "dealer_net_shares": "Dealers-Difference",
                "total_institutional_net_shares": "ThreeInstitutionalInvestorsTotal-Difference",
            },
            role="fallback",
            rate_limit="Latest daily TPEX OpenAPI snapshot.",
            failure_modes=["English field names contain spacing inconsistencies; adapter should use tolerant key matching."],
            recommendation="Prefer over old RWD table for OTC latest fallback.",
            notes=["Current OpenAPI avoids repeated column names but has awkward English keys."],
        ),
    )


def _probe_tpex_institutional_rwd(date: str) -> ChipSourceProbeResult:
    url = f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?date={date}&type=Daily&response=json"
    return _guarded(
        "TPEX_RWD_DAILY_TRADE",
        url,
        lambda: _tpex_table_result(
            name="TPEX_RWD_DAILY_TRADE",
            url=url,
            mapping={
                "ticker": "data[0] 代號",
                "name": "data[1] 名稱",
                "foreign_net_shares": "data[10] 外資及陸資買賣超股數",
                "investment_trust_net_shares": "data[13] 投信買賣超股數",
                "dealer_net_shares": "data[22] 自營商買賣超股數",
                "total_institutional_net_shares": "data[23] 三大法人買賣超股數合計",
            },
            role="fallback",
            rate_limit="Daily RWD endpoint; no documented app quota in response.",
            failure_modes=["Repeated field names require positional mapping.", "Date-sensitive; holidays return no data."],
            recommendation="Keep as secondary fallback after TPEX OpenAPI.",
            notes=["Existing implementation already uses positional mapping."],
        ),
    )


def _probe_tpex_margin_openapi() -> ChipSourceProbeResult:
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance"
    return _guarded(
        "TPEX_OPENAPI_MAINBOARD_MARGIN_BALANCE",
        url,
        lambda: _json_list_result(
            name="TPEX_OPENAPI_MAINBOARD_MARGIN_BALANCE",
            url=url,
            mapping={
                "date": "Date",
                "ticker": "SecuritiesCompanyCode",
                "name": "CompanyName",
                "margin_balance": "MarginPurchaseBalance",
                "short_balance": "ShortSaleBalance",
                "margin_buy": "MarginPurchase",
                "short_sell": "ShortSale",
            },
            role="fallback",
            rate_limit="Latest daily TPEX OpenAPI snapshot.",
            failure_modes=["Only latest snapshot; not enough alone for historical trend reconstruction."],
            recommendation="Use as OTC latest fallback and scheduler daily snapshot source.",
            notes=["Direct JSON list is easier than dated RWD table."],
        ),
    )


def _probe_tpex_margin_rwd(date: str) -> ChipSourceProbeResult:
    url = f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={date}&response=json"
    return _guarded(
        "TPEX_RWD_MARGIN_BALANCE",
        url,
        lambda: _tpex_table_result(
            name="TPEX_RWD_MARGIN_BALANCE",
            url=url,
            mapping={
                "ticker": "代號",
                "name": "名稱",
                "margin_balance": "資餘額",
                "short_balance": "券餘額",
                "margin_buy": "資買",
                "short_sell": "券賣",
            },
            role="fallback",
            rate_limit="Daily RWD endpoint; no documented app quota in response.",
            failure_modes=["Date-sensitive; holidays return no data."],
            recommendation="Keep as dated OTC fallback only.",
            notes=["Existing implementation already supports this endpoint."],
        ),
    )


def _probe_tpex_qfii_openapi() -> ChipSourceProbeResult:
    url = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_qfii"
    return _guarded(
        "TPEX_OPENAPI_3INSTI_QFII",
        url,
        lambda: _json_list_result(
            name="TPEX_OPENAPI_3INSTI_QFII",
            url=url,
            mapping={
                "date": "Date",
                "ticker": "SecuritiesCompanyCode",
                "name": "CompanyName",
                "foreign_holding_pct": "PercentageOfSharesOC/FMIHeld",
                "foreign_remaining_pct": "PercentageOfAvailableInvestmentForOC/FI",
            },
            role="fallback",
            rate_limit="Latest daily TPEX OpenAPI snapshot.",
            failure_modes=["OTC only; percentage fields include percent sign."],
            recommendation="Use as OTC qfiis_pct fallback; use FinMind if it covers required OTC tickers.",
            notes=["Covers TPEX foreign holding ratio with direct JSON."],
        ),
    )


def _probe_tpex_qfii_trading_openapi() -> ChipSourceProbeResult:
    url = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_qfii_trading"
    return _guarded(
        "TPEX_OPENAPI_3INSTI_QFII_TRADING",
        url,
        lambda: _json_list_result(
            name="TPEX_OPENAPI_3INSTI_QFII_TRADING",
            url=url,
            mapping={
                "date": "Date",
                "ticker": "SecuritiesCompanyCode",
                "foreign_buy_lots": "ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy",
                "foreign_sell_lots": "ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell",
                "foreign_net_lots": "ForeignInvestorsIncludeMainlandAreaInvestors-Difference",
            },
            role="diagnostic",
            rate_limit="Latest daily TPEX OpenAPI snapshot.",
            failure_modes=["Field names include inconsistent leading spaces in some rows."],
            recommendation="Use only if detailed OTC foreign trading ranking is needed.",
            notes=["Not required for Phase A core chip panel if daily trading endpoint is enough."],
        ),
    )


def _probe_mops_month_revenue(ticker: str, iso_date: str) -> ChipSourceProbeResult:
    year, month, _day = iso_date.split("-")
    roc_year = str(int(year) - 1911)
    url = "https://mops.twse.com.tw/mops/web/ajax_t05st10_ifrs"

    def run() -> ChipSourceProbeResult:
        text = fetch_text(
            url,
            data={
                "encodeURIComponent": "1",
                "step": "1",
                "firstin": "1",
                "off": "1",
                "queryName": "co_id",
                "inpuType": "co_id",
                "TYPEK": "all",
                "co_id": ticker,
                "year": roc_year,
                "month": str(int(month)),
            },
        )
        sample = {
            "html_bytes": len(text.encode("utf-8")),
            "contains_table": "<table" in text.lower(),
            "contains_ticker": ticker in text,
        }
        return ChipSourceProbeResult(
            name="MOPS_MONTH_REVENUE_HTML",
            status="ok" if sample["contains_table"] else "empty",
            source_url=url,
            records_count=1 if sample["contains_table"] else 0,
            sample=sample,
            mapping={
                "period": "HTML table ROC year/month",
                "revenue": "HTML table revenue column",
                "yoy_pct": "HTML table YoY column",
            },
            role="fallback",
            rate_limit="HTML POST endpoint; source update follows issuer monthly filing.",
            failure_modes=["HTML shape can change; parser is heuristic.", "MOPS may reject or throttle automated POST traffic."],
            recommendation="Keep as fallback after FinMind monthly revenue.",
            notes=["Existing revenue_fetcher uses this endpoint and SimpleTableParser."],
        )

    return _guarded("MOPS_MONTH_REVENUE_HTML", url, run)


def _probe_datagov_twse_qfiis_metadata() -> ChipSourceProbeResult:
    return _probe_datagov_metadata(
        name="DATAGOV_TWSE_QFIIS_METADATA",
        url="https://data.gov.tw/dataset/11655",
        role="metadata",
        recommendation="Use only to document license/OAS; call TWSE OpenAPI directly.",
        notes=[
            "Dataset describes listed-market foreign/mainland investment holding ratio by industry.",
            "Page points to TWSE OpenAPI swagger rather than a better direct data endpoint.",
        ],
    )


def _probe_datagov_tpex_institutional_metadata() -> ChipSourceProbeResult:
    return _probe_datagov_metadata(
        name="DATAGOV_TPEX_INSTITUTIONAL_METADATA",
        url="https://data.gov.tw/en/datasets/11743",
        role="metadata",
        recommendation="Use only to document license/OAS; call TPEX OpenAPI directly.",
        notes=[
            "Dataset describes OTC three major institutional summary.",
            "Page points to TPEX OpenAPI swagger.",
        ],
    )


def _probe_datagov_tpex_margin_metadata() -> ChipSourceProbeResult:
    return _probe_datagov_metadata(
        name="DATAGOV_TPEX_MARGIN_METADATA",
        url="https://data.gov.tw/en/datasets/11387",
        role="metadata",
        recommendation="Use only to document license/OAS; call TPEX OpenAPI directly.",
        notes=[
            "Dataset describes OTC financing/securities lending balance.",
            "Page points to TPEX OpenAPI swagger.",
        ],
    )


def _probe_datagov_metadata(
    name: str,
    url: str,
    role: str,
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    def run() -> ChipSourceProbeResult:
        text = fetch_text(url)
        sample = {
            "page_reachable": True,
            "html_bytes": len(text.encode("utf-8")),
            "contains_openapi": "openapi" in text.lower(),
            "contains_daily_update": ("每1日" in text) or ("Every day" in text),
        }
        return ChipSourceProbeResult(
            name=name,
            status="ok",
            source_url=url,
            records_count=1,
            sample=sample,
            mapping={
                "license": "data.gov.tw license metadata",
                "update_cadence": "data.gov.tw update frequency metadata",
                "oas_url": "data.gov.tw OAS/API documentation metadata",
            },
            role=role,
            rate_limit="Metadata page; not a production data path.",
            failure_modes=["HTML page may require JavaScript for some UI details.", "Not suitable as runtime data source."],
            recommendation=recommendation,
            notes=notes,
        )

    return _guarded(name, url, run)


def _finmind_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    role: str,
    rate_limit: str,
    failure_modes: list[str],
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    payload = json.loads(fetch_text(url))
    rows = payload.get("data") or []
    status_code = payload.get("status")
    if status_code != 200:
        raise ValueError(f"FinMind status={status_code}, msg={payload.get('msg')}")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"FinMind returned no rows, msg={payload.get('msg')}")
    return ChipSourceProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=rows[0],
        mapping=mapping,
        role=role,
        rate_limit=rate_limit,
        failure_modes=failure_modes,
        recommendation=recommendation,
        notes=notes,
    )


def _json_list_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    role: str,
    rate_limit: str,
    failure_modes: list[str],
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    rows = parse_json_list(fetch_text(url))
    if not rows:
        raise ValueError("JSON endpoint returned no rows")
    return ChipSourceProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=rows[0],
        mapping=mapping,
        role=role,
        rate_limit=rate_limit,
        failure_modes=failure_modes,
        recommendation=recommendation,
        notes=notes,
    )


def _twse_rwd_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    role: str,
    rate_limit: str,
    failure_modes: list[str],
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    fields, rows = parse_twse_rwd_table(fetch_text(url))
    sample = dict(zip(fields, rows[0], strict=False))
    return ChipSourceProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping=mapping,
        role=role,
        rate_limit=rate_limit,
        failure_modes=failure_modes,
        recommendation=recommendation,
        notes=notes,
    )


def _twse_margin_rwd_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    role: str,
    rate_limit: str,
    failure_modes: list[str],
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    payload = json.loads(fetch_text(url))
    if payload.get("stat") != "OK":
        raise ValueError(f"TWSE returned non-OK status: {payload.get('stat')}")
    tables = payload.get("tables") or []
    detail_table = None
    for table in tables:
        fields = table.get("fields") if isinstance(table, dict) else None
        rows = table.get("data") if isinstance(table, dict) else None
        if fields and rows and "代號" in fields and "名稱" in fields:
            detail_table = table
            break
    if not detail_table:
        raise ValueError("TWSE MI_MARGN RWD response has no detail table")

    fields = detail_table.get("fields") or []
    rows = detail_table.get("data") or []
    sample = {
        f"col_{idx:02d}_{field}": value
        for idx, (field, value) in enumerate(zip(fields, rows[0], strict=False))
    }
    return ChipSourceProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping=mapping,
        role=role,
        rate_limit=rate_limit,
        failure_modes=failure_modes,
        recommendation=recommendation,
        notes=notes,
    )


def _tpex_table_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    role: str,
    rate_limit: str,
    failure_modes: list[str],
    recommendation: str,
    notes: list[str],
) -> ChipSourceProbeResult:
    fields, rows = parse_tpex_table(fetch_text(url))
    sample = {
        f"col_{idx:02d}_{field}": value
        for idx, (field, value) in enumerate(zip(fields, rows[0], strict=False))
    }
    return ChipSourceProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping=mapping,
        role=role,
        rate_limit=rate_limit,
        failure_modes=failure_modes,
        recommendation=recommendation,
        notes=notes,
    )


def _guarded(
    name: str,
    url: str,
    run: Callable[[], ChipSourceProbeResult],
) -> ChipSourceProbeResult:
    try:
        return run()
    except Exception as exc:
        return ChipSourceProbeResult(
            name=name,
            status="failed",
            source_url=url,
            records_count=0,
            sample={"error": f"{type(exc).__name__}: {exc}"},
            mapping={},
            role="unknown",
            rate_limit="unknown",
            failure_modes=[f"{type(exc).__name__}: {exc}"],
            recommendation="Do not depend on this source until a follow-up probe succeeds.",
            notes=[],
        )


def _finmind_url(dataset: str, ticker: str, start_date: str, end_date: str) -> str:
    params = {
        "dataset": dataset,
        "start_date": start_date,
        "end_date": end_date,
    }
    if ticker:
        params["data_id"] = ticker
    token = os.getenv("FINMIND_API_TOKEN", "").strip()
    if token:
        params["token"] = token
    return f"https://api.finmindtrade.com/api/v4/data?{urlencode(params)}"


def _finmind_rate_limit_note() -> str:
    if os.getenv("FINMIND_API_TOKEN", "").strip():
        return "FINMIND_API_TOKEN was set for this probe; still add source_health logging in production."
    return "Probe ran without FINMIND_API_TOKEN; tokenless access worked in this run but may be throttled."


def _redact_url(url: str) -> str:
    token = os.getenv("FINMIND_API_TOKEN", "").strip()
    if token:
        return url.replace(token, "***")
    return url


def _yyyymmdd(value: str) -> str:
    return value.replace("-", "").replace("/", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe chip/fundamental data sources for Phase A-A0.")
    parser.add_argument("--ticker", default=DEFAULT_TICKER, help="Taiwan stock code without suffix, e.g. 2330")
    parser.add_argument("--date", default=DEFAULT_DATE, help="Probe date in YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Historical probe start date in YYYY-MM-DD")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE, help="Historical probe end date in YYYY-MM-DD")
    parser.add_argument("--markdown", default="docs/data_source_mapping_20260503.md")
    parser.add_argument("--json", default="docs/data_source_mapping_20260503.json")
    args = parser.parse_args()

    results = run_all_probes(
        ticker=args.ticker,
        probe_date=args.date,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    write_artifacts(results, markdown_path=args.markdown, json_path=args.json)

    print(f"Wrote {args.markdown}")
    print(f"Wrote {args.json}")
    for result in results:
        print(f"{result.status:7} {result.records_count:5} {result.name}")


if __name__ == "__main__":
    main()
