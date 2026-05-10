from __future__ import annotations


def ticker_to_tv_symbol(ticker: str) -> str:
    """Convert a yfinance ticker to a TradingView symbol string.

    Taiwan tickers use TPE: (TWSE) or TPEX: (OTC) prefixes.
    US tickers are passed through as-is — TradingView auto-resolves them.
    """
    t = ticker.strip().upper()
    if t.endswith(".TW"):
        return f"TPE:{t[:-3]}"
    if t.endswith(".TWO"):
        return f"TPEX:{t[:-4]}"
    return t
