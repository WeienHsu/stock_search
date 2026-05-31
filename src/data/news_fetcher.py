from datetime import datetime, timedelta

import finnhub
import streamlit as st

from src.core.finnhub_mode import resolve_api_key
from src.core.market_calendar import cache_ttl_seconds
from src.data.dynamic_ttl import get_ttl
from src.data.source_resolution import fetch_with_source_fallback
from src.repositories.news_cache_repo import get_news_cache, save_news_cache
from src.repositories.source_health_repo import record_source_health


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_news(ticker: str, user_id: str) -> list[dict]:
    cached = get_news_cache(ticker, ttl_override=cache_ttl_seconds(ticker, "news"))
    if cached is not None:
        return cached

    articles = fetch_with_source_fallback(
        ["finnhub"],
        lambda source_id: _fetch_finnhub_news(ticker, user_id),
        lambda result: isinstance(result, list) and len(result) > 0,
        empty_result=[],
        on_success=lambda source_id, result: record_source_health(source_id, "ok"),
        on_failure=lambda source_id, reason: record_source_health(source_id, "unavailable", reason=reason[:200]),
    )
    if articles:
        save_news_cache(ticker, articles)
    return articles


def _fetch_finnhub_news(ticker: str, user_id: str) -> list[dict]:
    api_key = resolve_api_key(user_id)  # raises MissingFinnhubKey if not configured
    client = finnhub.Client(api_key=api_key)

    to_date = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")

    # Finnhub uses plain symbol without exchange suffix (e.g. "2330" not "2330.TW")
    symbol = ticker.split(".")[0] if "." in ticker else ticker

    return client.company_news(symbol, _from=from_date, to=to_date) or []
