"""Realtime-ish quotes: TWSE/TPEX via MIS API (batch), US via yfinance fast_info.

Results are cached in-process for a few seconds so a polling UI does not
hammer upstream endpoints.
"""

import re
import time
from typing import Any

import requests

_TW_PATTERN = re.compile(r"^(\d{4,6}[A-Z]?)\.(TW|TWO)$")
_MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
_HEADERS = {"User-Agent": "Mozilla/5.0"}

_CACHE_TTL = 5.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def fetch_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    """Return quote dicts for mixed TW/US symbols, preserving input order."""
    now = time.time()
    fresh: dict[str, dict[str, Any]] = {
        sym: entry for sym, (ts, entry) in _cache.items() if now - ts < _CACHE_TTL
    }
    tw_missing = [s for s in symbols if _TW_PATTERN.match(s) and s not in fresh]
    us_missing = [s for s in symbols if not _TW_PATTERN.match(s) and s not in fresh]

    fetched: dict[str, dict[str, Any]] = {}
    if tw_missing:
        fetched.update(_fetch_tw_quotes(tw_missing))
    for sym in us_missing:
        quote = _fetch_us_quote(sym)
        if quote:
            fetched[sym] = quote
    for sym, quote in fetched.items():
        _cache[sym] = (now, quote)

    merged = {**fresh, **fetched}
    return [merged[s] for s in symbols if s in merged]


def _fetch_tw_quotes(symbols: list[str]) -> dict[str, dict[str, Any]]:
    ex_ch = "|".join(
        f"{'tse' if m.group(2) == 'TW' else 'otc'}_{m.group(1).lower()}.tw"
        for m in (_TW_PATTERN.match(s) for s in symbols)
        if m
    )
    try:
        resp = requests.get(
            _MIS_URL,
            params={"ex_ch": ex_ch, "json": "1", "delay": "0"},
            headers=_HEADERS,
            timeout=5,
        )
        resp.raise_for_status()
        rows = resp.json().get("msgArray", [])
    except Exception:
        return {}

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        quote = parse_mis_row(row)
        if quote:
            result[quote["symbol"]] = quote
    return result


def parse_mis_row(row: dict[str, Any]) -> dict[str, Any] | None:
    code = row.get("c")
    if not code:
        return None
    suffix = ".TWO" if row.get("ex") == "otc" else ".TW"
    prev_close = _num(row.get("y"))
    # z is "-" outside matched trades; fall back to best bid, then prev close
    price = _num(row.get("z"))
    if price is None:
        bids = str(row.get("b") or "").split("_")
        price = _num(bids[0]) if bids else None
    if price is None:
        price = prev_close
    if price is None:
        return None
    change = price - prev_close if prev_close else 0.0
    return {
        "symbol": f"{code}{suffix}",
        "name": row.get("n", ""),
        "price": price,
        "prev_close": prev_close,
        "change": round(change, 4),
        "change_pct": round(change / prev_close * 100, 2) if prev_close else 0.0,
        "open": _num(row.get("o")),
        "high": _num(row.get("h")),
        "low": _num(row.get("l")),
        "volume": _num(row.get("v")),
        "market": "TW",
        "ts": int(int(row["tlong"]) / 1000) if row.get("tlong") else int(time.time()),
    }


def _fetch_us_quote(symbol: str) -> dict[str, Any] | None:
    import yfinance as yf

    try:
        info = yf.Ticker(symbol).fast_info
        price = float(info["last_price"])
        prev_close = float(info["previous_close"])
    except Exception:
        return None
    change = price - prev_close if prev_close else 0.0
    return {
        "symbol": symbol,
        "name": "",
        "price": round(price, 4),
        "prev_close": round(prev_close, 4),
        "change": round(change, 4),
        "change_pct": round(change / prev_close * 100, 2) if prev_close else 0.0,
        "open": _opt_float(info, "open"),
        "high": _opt_float(info, "day_high"),
        "low": _opt_float(info, "day_low"),
        "volume": _opt_float(info, "last_volume"),
        "market": "US",
        "ts": int(time.time()),
    }


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _opt_float(info: Any, key: str) -> float | None:
    try:
        return float(info[key])
    except Exception:
        return None
