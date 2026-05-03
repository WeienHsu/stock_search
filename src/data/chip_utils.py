from __future__ import annotations

from typing import Literal

MarketKind = Literal["twse", "tpex", "unsupported"]


def market_kind(ticker: str) -> MarketKind:
    normalized = ticker.strip().upper()
    if normalized.endswith(".TW"):
        return "twse"
    if normalized.endswith(".TWO"):
        return "tpex"
    return "unsupported"


def is_taiwan_ticker(ticker: str) -> bool:
    return market_kind(ticker) != "unsupported"


def is_probable_taiwan_etf(ticker: str) -> bool:
    code = ticker_code(ticker)
    return market_kind(ticker) != "unsupported" and code.startswith("00")


def ticker_code(ticker: str) -> str:
    return ticker.strip().upper().split(".", 1)[0]
