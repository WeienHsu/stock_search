import math
from typing import Any

from fastapi import APIRouter

from src.data.index_fetcher import (
    enrich_index_indicators,
    fetch_index_ohlcv,
    get_taiex_realtime_breadth,
    index_snapshot,
)
from src.data.market_sentiment_fetcher import fetch_cnn_fear_greed
from src.data.twse_fetcher import fetch_institutional_flow

router = APIRouter(tags=["market"])

_INDICES = {
    "taiex": "^TWII",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "usdtwd": "TWD=X",
}


@router.get("/market")
def market_overview() -> dict:
    indices: dict[str, Any] = {}
    for key, symbol in _INDICES.items():
        try:
            df = enrich_index_indicators(fetch_index_ohlcv(symbol, period="6mo"))
            indices[key] = index_snapshot(df)
        except Exception:
            indices[key] = {}

    return {
        "indices": indices,
        "breadth": _safe(get_taiex_realtime_breadth),
        "fear_greed": _safe(fetch_cnn_fear_greed),
        "institutional": _safe(_institutional_rows) or [],
    }


def _institutional_rows() -> list[dict]:
    df = fetch_institutional_flow(days=10)
    rows = df.to_dict("records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows


def _safe(fn) -> Any:
    try:
        return fn()
    except Exception:
        return None
