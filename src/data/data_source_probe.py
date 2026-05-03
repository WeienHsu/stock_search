from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yfinance as yf

DEFAULT_PROBE_DATE = "20260430"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


@dataclass
class ProbeResult:
    name: str
    status: str
    source_url: str
    records_count: int
    sample: dict[str, Any]
    mapping: dict[str, str]
    notes: list[str]


class SimpleTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._in_row = True
            self._current_row = []
        if tag.lower() in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._in_cell:
            value = " ".join("".join(self._buffer).split())
            if value:
                self._current_row.append(value)
            self._in_cell = False
        if tag.lower() == "tr" and self._in_row:
            if self._current_row:
                self.rows.append(self._current_row)
            self._in_row = False


def fetch_text(url: str, data: dict[str, str] | None = None) -> str:
    encoded_data = urlencode(data).encode("utf-8") if data else None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html,text/plain,*/*",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    if "twse.com.tw" in url:
        headers["Referer"] = "https://www.twse.com.tw/zh/"
    elif "tpex.org.tw" in url:
        headers["Referer"] = "https://www.tpex.org.tw/www/zh-tw/"
    elif "cnn.com" in url:
        headers["Referer"] = "https://www.cnn.com/markets/fear-and-greed"
    request = Request(
        url,
        data=encoded_data,
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_json_list(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON list")
    return [row for row in data if isinstance(row, dict)]


def parse_twse_rwd_table(text: str) -> tuple[list[str], list[list[str]]]:
    data = json.loads(text)
    fields = data.get("fields") or []
    rows = data.get("data") or []
    if data.get("stat") != "OK":
        raise ValueError(f"TWSE returned non-OK status: {data.get('stat')}")
    if not fields or not rows:
        raise ValueError("TWSE RWD table has no fields or rows")
    return fields, rows


def parse_tpex_table(text: str) -> tuple[list[str], list[list[str]]]:
    data = json.loads(text)
    tables = data.get("tables") or []
    if not tables:
        raise ValueError("TPEX response has no tables")
    table = tables[0]
    fields = table.get("fields") or []
    rows = table.get("data") or []
    if not fields or not rows:
        raise ValueError("TPEX table has no fields or rows")
    return fields, rows


def parse_cnn_fear_greed(text: str) -> dict[str, Any]:
    data = json.loads(text)
    current = data.get("fear_and_greed") or {}
    historical = data.get("fear_and_greed_historical") or {}
    if "score" not in current:
        raise ValueError("CNN response missing fear_and_greed.score")
    return {
        "score": current.get("score"),
        "rating": current.get("rating"),
        "timestamp": current.get("timestamp"),
        "historical_points": len(historical.get("data") or []),
    }


def parse_taifex_futures_html(text: str) -> list[dict[str, Any]]:
    parser = SimpleTableParser()
    parser.feed(text)

    parsed: list[dict[str, Any]] = []
    current_product = ""
    for row in parser.rows:
        if len(row) >= 15 and row[2] in {"自營商", "投信", "外資"}:
            current_product = row[1]
            parsed.append(_taifex_row_to_record(current_product, row[2], row[3:]))
        elif len(row) >= 13 and row[0] in {"自營商", "投信", "外資"}:
            parsed.append(_taifex_row_to_record(current_product, row[0], row[1:]))

    if not parsed:
        raise ValueError("TAIFEX HTML table has no institutional futures rows")
    return parsed


def parse_barchart_mmfi(text: str) -> dict[str, Any]:
    symbol_match = re.search(r'"symbol"\s*:\s*"\$MMFI"', text)
    price_match = re.search(r'"lastPrice"\s*:\s*"?([0-9.]+)"?', text)
    trade_time_match = re.search(r'"tradeTime"\s*:\s*"([^"]+)"', text)
    if not symbol_match or not price_match:
        raise ValueError("Barchart page missing $MMFI currentSymbol price")
    return {
        "symbol": "$MMFI",
        "last_price": float(price_match.group(1)),
        "trade_time": trade_time_match.group(1) if trade_time_match else "",
    }


def run_all_probes(probe_date: str = DEFAULT_PROBE_DATE) -> list[ProbeResult]:
    twse_date = _yyyymmdd(probe_date)
    slash_date = f"{twse_date[:4]}/{twse_date[4:6]}/{twse_date[6:]}"

    probes = [
        _probe_twse_t86(twse_date),
        _probe_twse_margin(),
        _probe_twse_bwiddu(),
        _probe_tpex_institutional(slash_date),
        _probe_tpex_margin(slash_date),
        _probe_taifex_futures(slash_date),
        _probe_cnn_fear_greed(twse_date),
        _probe_mmfi_yfinance(),
        _probe_mmfi_barchart(),
    ]
    return probes


def write_probe_artifacts(
    results: list[ProbeResult],
    markdown_path: str = "docs/data_source_mapping_P0_5.md",
    json_path: str = "docs/data_source_mapping_P0_5.json",
) -> None:
    from pathlib import Path

    Path(markdown_path).write_text(render_markdown(results), encoding="utf-8")
    Path(json_path).write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_markdown(results: list[ProbeResult]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# P0.5 Data Source Mapping",
        "",
        f"Generated at: {generated_at}",
        "",
        "## Summary",
        "",
        "| Source | Status | Records | Notes |",
        "|--------|--------|---------|-------|",
    ]
    for result in results:
        notes = "<br>".join(result.notes)
        lines.append(
            f"| {result.name} | {result.status} | {result.records_count} | {notes} |"
        )

    lines.extend(["", "## Field Mapping", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- URL: `{result.source_url}`",
                f"- Status: `{result.status}`",
                f"- Records: `{result.records_count}`",
                "",
                "| Canonical Field | Source Field |",
                "|-----------------|--------------|",
            ]
        )
        for canonical, source in result.mapping.items():
            lines.append(f"| `{canonical}` | `{source}` |")
        lines.extend(["", "Sample:", "", "```json"])
        lines.append(json.dumps(result.sample, ensure_ascii=False, indent=2))
        lines.extend(["```", ""])

    return "\n".join(lines)


def _probe_twse_t86(date: str) -> ProbeResult:
    url = (
        "https://www.twse.com.tw/rwd/zh/fund/T86"
        f"?date={date}&selectType=ALLBUT0999&response=json"
    )
    return _guarded_probe(
        "TWSE_T86_LISTED_INSTITUTIONAL",
        url,
        lambda: _twse_t86_result(url),
    )


def _twse_t86_result(url: str) -> ProbeResult:
    fields, rows = parse_twse_rwd_table(fetch_text(url))
    sample = dict(zip(fields, rows[0], strict=False))
    return ProbeResult(
        name="TWSE_T86_LISTED_INSTITUTIONAL",
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping={
            "ticker": "證券代號",
            "name": "證券名稱",
            "foreign_net_shares": "外陸資買賣超股數(不含外資自營商)",
            "investment_trust_net_shares": "投信買賣超股數",
            "dealer_net_shares": "自營商買賣超股數",
            "total_institutional_net_shares": "三大法人買賣超股數",
        },
        notes=["上市個股三大法人買賣超；P1.5/P2.6 可用。"],
    )


def _probe_twse_margin() -> ProbeResult:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"
    return _guarded_probe(
        "TWSE_MI_MARGN_LISTED_MARGIN",
        url,
        lambda: _json_list_result(
            name="TWSE_MI_MARGN_LISTED_MARGIN",
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
            notes=["上市融資融券餘額；OpenAPI JSON 可直接解析。"],
        ),
    )


def _probe_twse_bwiddu() -> ProbeResult:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_d"
    return _guarded_probe(
        "TWSE_BWIBBU_D_VALUATION_ONLY",
        url,
        lambda: _json_list_result(
            name="TWSE_BWIBBU_D_VALUATION_ONLY",
            url=url,
            mapping={
                "date": "Date",
                "ticker": "Code",
                "name": "Name",
                "close": "ClosePrice",
                "dividend_yield": "DividendYield",
                "pe_ratio": "PEratio",
                "pb_ratio": "PBratio",
            },
            notes=["估值資料，不是法人買賣超；不得用於外資/投信流向。"],
        ),
    )


def _probe_tpex_institutional(date: str) -> ProbeResult:
    url = (
        "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
        f"?date={date}&type=Daily&response=json"
    )
    return _guarded_probe(
        "TPEX_DAILY_TRADE_OTC_INSTITUTIONAL",
        url,
        lambda: _tpex_institutional_result(url),
    )


def _probe_tpex_margin(date: str) -> ProbeResult:
    url = f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={date}&response=json"
    return _guarded_probe(
        "TPEX_MARGIN_OTC",
        url,
        lambda: _tpex_table_result(
            name="TPEX_MARGIN_OTC",
            url=url,
            mapping={
                "ticker": "代號",
                "name": "名稱",
                "margin_previous_balance": "前資餘額(張)",
                "margin_buy": "資買",
                "margin_sell": "資賣",
                "margin_balance": "資餘額",
                "short_previous_balance": "前券餘額(張)",
                "short_sell": "券賣",
                "short_buy": "券買",
                "short_balance": "券餘額",
            },
            notes=["上櫃融資融券；JSON table 可解析。"],
        ),
    )


def _probe_taifex_futures(date: str) -> ProbeResult:
    url = "https://www.taifex.com.tw/cht/3/futContractsDate"

    def run() -> ProbeResult:
        text = fetch_text(
            url,
            data={"queryDate": date, "commodityId": "TXF", "button": "送出查詢"},
        )
        records = parse_taifex_futures_html(text)
        return ProbeResult(
            name="TAIFEX_TXF_INSTITUTIONAL_OI",
            status="ok",
            source_url=url,
            records_count=len(records),
            sample=records[0],
            mapping={
                "product": "商品名稱",
                "identity": "身份別",
                "open_interest_long_contracts": "未平倉餘額 / 多方 / 口數",
                "open_interest_short_contracts": "未平倉餘額 / 空方 / 口數",
                "open_interest_net_contracts": "未平倉餘額 / 多空淨額 / 口數",
            },
            notes=["HTML form POST；需用 HTML table parser，無穩定 JSON endpoint。"],
        )

    return _guarded_probe("TAIFEX_TXF_INSTITUTIONAL_OI", url, run)


def _probe_cnn_fear_greed(date: str) -> ProbeResult:
    url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{date[:4]}-{date[4:6]}-{date[6:]}"

    def run() -> ProbeResult:
        sample = parse_cnn_fear_greed(fetch_text(url))
        return ProbeResult(
            name="CNN_FEAR_GREED",
            status="ok",
            source_url=url,
            records_count=max(1, int(sample.get("historical_points") or 0)),
            sample=sample,
            mapping={
                "score": "fear_and_greed.score",
                "rating": "fear_and_greed.rating",
                "timestamp": "fear_and_greed.timestamp",
                "history": "fear_and_greed_historical.data",
            },
            notes=["非正式 API；必須帶 browser-like headers，且需要 fallback。"],
        )

    return _guarded_probe("CNN_FEAR_GREED", url, run)


def _probe_mmfi_yfinance() -> ProbeResult:
    url = "yfinance:^MMFI"

    def run() -> ProbeResult:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            df = yf.download("^MMFI", period="5d", auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError("^MMFI returned empty DataFrame")
        latest = df.tail(1).reset_index().to_dict(orient="records")[0]
        return ProbeResult(
            name="MMFI_YFINANCE",
            status="ok",
            source_url=url,
            records_count=len(df),
            sample={str(k): str(v) for k, v in latest.items()},
            mapping={"value": "Close", "date": "Date"},
            notes=["原計畫來源。"],
        )

    return _guarded_probe("MMFI_YFINANCE", url, run)


def _probe_mmfi_barchart() -> ProbeResult:
    url = "https://www.barchart.com/stocks/quotes/%24MMFI"

    def run() -> ProbeResult:
        sample = parse_barchart_mmfi(fetch_text(url))
        return ProbeResult(
            name="MMFI_BARCHART_FALLBACK",
            status="ok",
            source_url=url,
            records_count=1,
            sample=sample,
            mapping={
                "symbol": "currentSymbol.symbol",
                "value": "currentSymbol.lastPrice",
                "trade_time": "currentSymbol.tradeTime",
            },
            notes=["yfinance ^MMFI 目前不可用；Barchart HTML 可作臨時 fallback。"],
        )

    return _guarded_probe("MMFI_BARCHART_FALLBACK", url, run)


def _json_list_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    notes: list[str],
) -> ProbeResult:
    rows = parse_json_list(fetch_text(url))
    return ProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=rows[0],
        mapping=mapping,
        notes=notes,
    )


def _tpex_table_result(
    name: str,
    url: str,
    mapping: dict[str, str],
    notes: list[str],
) -> ProbeResult:
    fields, rows = parse_tpex_table(fetch_text(url))
    sample = dict(zip(fields, rows[0], strict=False))
    return ProbeResult(
        name=name,
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping=mapping,
        notes=notes,
    )


def _tpex_institutional_result(url: str) -> ProbeResult:
    fields, rows = parse_tpex_table(fetch_text(url))
    sample = {
        f"col_{idx:02d}_{field}": value
        for idx, (field, value) in enumerate(zip(fields, rows[0], strict=False))
    }
    return ProbeResult(
        name="TPEX_DAILY_TRADE_OTC_INSTITUTIONAL",
        status="ok",
        source_url=url,
        records_count=len(rows),
        sample=sample,
        mapping={
            "ticker": "data[0] 代號",
            "name": "data[1] 名稱",
            "foreign_ex_dealer_net_shares": "data[4] 外資及陸資(不含外資自營商)買賣超股數",
            "foreign_dealer_net_shares": "data[7] 外資自營商買賣超股數",
            "foreign_net_shares": "data[10] 外資及陸資買賣超股數",
            "investment_trust_net_shares": "data[13] 投信買賣超股數",
            "dealer_self_net_shares": "data[16] 自營商(自行買賣)買賣超股數",
            "dealer_hedge_net_shares": "data[19] 自營商(避險)買賣超股數",
            "dealer_net_shares": "data[22] 自營商買賣超股數",
            "total_institutional_net_shares": "data[23] 三大法人買賣超股數合計",
        },
        notes=["上櫃三大法人買賣超；JSON 欄名重複，必須使用位置 mapping。"],
    )


def _taifex_row_to_record(product: str, identity: str, values: list[str]) -> dict[str, Any]:
    return {
        "product": product,
        "identity": identity,
        "trading_long_contracts": values[0],
        "trading_short_contracts": values[2],
        "trading_net_contracts": values[4],
        "open_interest_long_contracts": values[6],
        "open_interest_short_contracts": values[8],
        "open_interest_net_contracts": values[10],
    }


def _guarded_probe(name: str, url: str, probe: Any) -> ProbeResult:
    try:
        return probe()
    except (ValueError, URLError, TimeoutError, OSError) as exc:
        return ProbeResult(
            name=name,
            status="failed",
            source_url=url,
            records_count=0,
            sample={},
            mapping={},
            notes=[str(exc)],
        )


def _yyyymmdd(value: str) -> str:
    cleaned = value.replace("-", "").replace("/", "")
    if len(cleaned) != 8 or not cleaned.isdigit():
        raise ValueError("probe date must be YYYYMMDD, YYYY-MM-DD, or YYYY/MM/DD")
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe P0.5 market data sources.")
    parser.add_argument("--date", default=DEFAULT_PROBE_DATE, help="Probe date, e.g. 20260430")
    parser.add_argument("--markdown", default="docs/data_source_mapping_P0_5.md")
    parser.add_argument("--json", default="docs/data_source_mapping_P0_5.json")
    args = parser.parse_args()

    results = run_all_probes(args.date)
    write_probe_artifacts(results, markdown_path=args.markdown, json_path=args.json)
    print(render_markdown(results))


if __name__ == "__main__":
    main()
