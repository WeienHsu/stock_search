import math
from typing import Any

import pandas as pd
from fastapi import APIRouter

from src.data.chip_fetcher import fetch_chip_snapshot
from src.data.ticker_utils import normalize_ticker

router = APIRouter(tags=["chip"])


@router.get("/chip/{symbol}")
def chip(symbol: str, institutional_days: int = 10, margin_days: int = 20) -> dict:
    snapshot = fetch_chip_snapshot(
        normalize_ticker(symbol),
        institutional_days=institutional_days,
        margin_days=margin_days,
    )
    if not snapshot.get("supported"):
        return {"supported": False, "ticker": snapshot.get("ticker", symbol)}
    return {
        "supported": True,
        "ticker": snapshot.get("ticker"),
        "summary": snapshot.get("summary") or {},
        "qfiis_pct": snapshot.get("qfiis_pct"),
        "institutional": _records(snapshot.get("institutional")),
        "margin": _records(snapshot.get("margin")),
    }


def _records(df: Any) -> list[dict]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    rows = df.to_dict("records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows
