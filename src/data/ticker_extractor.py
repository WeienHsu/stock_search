from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from src.data.ticker_utils import normalize_ticker
from src.ui.nav.ticker_index import _ALIASES, build_ticker_index

_SETTINGS_PATH = Path(__file__).parents[2] / "config" / "default_settings.json"
_TEXT_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9.])\$?([A-Z]{1,5}|\d{4,5}(?:\.(?:TW|TWO))?)(?![A-Z0-9.])",
    re.IGNORECASE,
)
_CSV_TICKER_FIELDS = ("ticker", "symbol", "代碼", "股票代號")
_CSV_NAME_FIELDS = ("name", "名稱", "股票名稱")


def extract_tickers_from_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for match in _TEXT_TOKEN_RE.finditer(text or ""):
        token = match.group(1)
        normalized = normalize_ticker(token)
        if token.isalpha() and token != token.upper() and not _lookup_name(normalized):
            continue
        rows.append(_ticker_row(token))
    return _dedupe(rows)


def extract_tickers_from_csv(data: str | bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig") if isinstance(data, bytes) else str(data or "")
    if not text.strip():
        return []

    sample = io.StringIO(text)
    try:
        reader = csv.DictReader(sample)
        if reader.fieldnames:
            rows = []
            for raw in reader:
                ticker = _first_value(raw, _CSV_TICKER_FIELDS)
                name = _first_value(raw, _CSV_NAME_FIELDS)
                if ticker:
                    rows.append(_ticker_row(ticker, name=name))
            if rows:
                return _dedupe(rows)
    except csv.Error:
        pass

    parsed: list[dict[str, str]] = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        ticker = str(row[0]).strip()
        name = str(row[1]).strip() if len(row) > 1 else ""
        parsed.append(_ticker_row(ticker, name=name))
    return _dedupe(parsed)


def _ticker_row(raw_ticker: str, *, name: str = "") -> dict[str, str]:
    ticker = normalize_ticker(str(raw_ticker).strip())
    return {"ticker": ticker, "name": str(name).strip() or _lookup_name(ticker)}


def _lookup_name(ticker: str) -> str:
    if not ticker:
        return ""
    for item in _default_index():
        if str(item.get("ticker", "")).upper() == ticker.upper():
            return str(item.get("name", ""))
    if ticker in _ALIASES:
        return str(_ALIASES[ticker][0])
    return ""


def _default_index() -> list[dict[str, Any]]:
    try:
        defaults = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8")).get("watchlist_defaults", [])
    except Exception:
        defaults = []
    return build_ticker_index([], defaults)


def _first_value(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for field in fields:
        value = row.get(field)
        if value is None:
            value = lowered.get(field.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _dedupe(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        result.append({"ticker": ticker, "name": str(row.get("name") or "")})
    return result
