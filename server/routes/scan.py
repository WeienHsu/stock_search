import math

from fastapi import APIRouter

from server.routes import USER_ID
from src.core.strategy_registry import get as get_strategy
from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist

router = APIRouter(tags=["scan"])


@router.get("/scan")
def scan(strategy_id: str = "strategy_d") -> list[dict]:
    items = get_watchlist(USER_ID)
    if not items:
        return []
    strategy = get_strategy(strategy_id)
    df = scan_watchlist(items, strategy_id, strategy.default_params())
    rows = df.to_dict("records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows
