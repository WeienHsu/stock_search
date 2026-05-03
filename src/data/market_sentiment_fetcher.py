from __future__ import annotations

import re
from datetime import date
from typing import Any

from src.data.data_source_probe import fetch_text, parse_barchart_mmfi, parse_cnn_fear_greed
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache


def fetch_cnn_fear_greed() -> dict[str, Any]:
    cache_key = "cnn_fear_greed"
    cached = get_market_cache(cache_key, ttl_override=3600)
    if isinstance(cached, dict) and cached:
        return cached

    today = date.today().strftime("%Y-%m-%d")
    url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{today}"
    result = parse_cnn_fear_greed(fetch_text(url))
    save_market_cache(cache_key, result)
    return result


def fetch_mmfi() -> dict[str, Any]:
    cache_key = "mmfi_barchart"
    cached = get_market_cache(cache_key, ttl_override=3600)
    if isinstance(cached, dict) and cached:
        return cached

    url = "https://www.barchart.com/stocks/quotes/%24MMFI"
    result = parse_barchart_mmfi(fetch_text(url))
    save_market_cache(cache_key, result)
    return result
