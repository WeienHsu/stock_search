from datetime import datetime, timedelta

import finnhub

from src.core.finnhub_mode import resolve_api_key
from src.repositories.news_cache_repo import get_news_cache, save_news_cache


def fetch_news(ticker: str, user_id: str) -> list[dict]:
    cached = get_news_cache(ticker)
    if cached is not None:
        return cached

    api_key = resolve_api_key(user_id)  # raises MissingFinnhubKey if not configured
    client = finnhub.Client(api_key=api_key)

    to_date = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")

    # Finnhub uses plain symbol without exchange suffix (e.g. "2330" not "2330.TW")
    symbol = ticker.split(".")[0] if "." in ticker else ticker

    articles = client.company_news(symbol, _from=from_date, to=to_date) or []

    if isinstance(articles, list):
        save_news_cache(ticker, articles)

    return articles
