import re


def normalize_ticker(ticker: str) -> str:
    if not ticker:
        return ""
    ticker = ticker.strip().upper()
    # Pure 4–5 digit number → Taiwan stock, append .TW
    if re.fullmatch(r"\d{4,5}", ticker):
        ticker = ticker + ".TW"
    return ticker


def normalize_ticker_with_fallback(ticker: str) -> list[str]:
    """Return yfinance ticker candidates in preferred lookup order."""
    normalized = normalize_ticker(ticker)
    if not normalized:
        return []

    match = re.fullmatch(r"(\d{4,5})(?:\.(TW|TWO))?", normalized)
    if not match:
        return [normalized]

    code = match.group(1)
    suffix = match.group(2)
    if suffix == "TWO":
        return [f"{code}.TWO"]
    return [f"{code}.TW", f"{code}.TWO"]
