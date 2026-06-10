from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.routes import USER_ID
from src.data.realtime_quote import fetch_quotes
from src.data.ticker_utils import normalize_ticker
from src.repositories.watchlist_repo import add_ticker, get_watchlist, remove_ticker

router = APIRouter(tags=["watchlist"])


class WatchlistItem(BaseModel):
    ticker: str
    name: str = ""


@router.get("/watchlist")
def list_watchlist() -> list[dict]:
    return get_watchlist(USER_ID)


@router.post("/watchlist")
def add_watchlist_item(item: WatchlistItem) -> dict:
    ticker = normalize_ticker(item.ticker)
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    name = item.name.strip()
    if not name:
        quotes = fetch_quotes([ticker])
        name = quotes[0].get("name", "") if quotes else ""
    add_ticker(USER_ID, ticker, name)
    return {"ticker": ticker, "name": name}


@router.delete("/watchlist/{ticker}")
def delete_watchlist_item(ticker: str) -> dict:
    remove_ticker(USER_ID, normalize_ticker(ticker))
    return {"ok": True}
