from fastapi import APIRouter, Query

from src.data.realtime_quote import fetch_quotes
from src.data.ticker_utils import normalize_ticker

router = APIRouter(tags=["quotes"])


@router.get("/quotes")
def get_quotes(symbols: str = Query(..., description="comma-separated tickers")) -> list[dict]:
    tickers = [normalize_ticker(s) for s in symbols.split(",") if s.strip()]
    return fetch_quotes(tickers)
