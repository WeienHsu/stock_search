import re


def normalize_ticker(ticker: str) -> str:
    if not ticker:
        return ""
    ticker = ticker.strip().upper()
    # Pure 4–5 digit number → Taiwan stock, append .TW
    if re.fullmatch(r"\d{4,5}", ticker):
        ticker = ticker + ".TW"
    return ticker
