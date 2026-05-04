from __future__ import annotations

TW_STOCK_SYNONYMS: dict[str, list[str]] = {
    "2330.TW": ["台積電", "tsmc", "護國神山"],
    "2317.TW": ["鴻海", "foxconn"],
    "2382.TW": ["廣達", "廣達電腦"],
    "3037.TW": ["欣興", "欣興電子"],
    "2303.TW": ["聯電", "umc"],
    "2454.TW": ["聯發科", "mediatek"],
    "6491.TW": ["晶碩"],
    "6757.TW": ["台灣虎航"],
}


def query_terms_for_ticker(ticker: str) -> list[str]:
    normalized = ticker.upper()
    symbol = normalized.split(".")[0]
    terms = [symbol, normalized, *TW_STOCK_SYNONYMS.get(normalized, [])]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        value = str(term).strip()
        key = value.lower()
        if value and key not in seen:
            deduped.append(value)
            seen.add(key)
    return deduped
