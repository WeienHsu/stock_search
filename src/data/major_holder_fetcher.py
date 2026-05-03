from __future__ import annotations

from typing import Any

import pandas as pd

from src.data.chip_data_sources import build_default_chain
from src.data.chip_utils import is_taiwan_ticker, market_kind, ticker_code
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache
from src.repositories.source_health_repo import record_source_health

_DAY = 24 * 3600


def fetch_major_holder_snapshot(ticker: str) -> dict[str, Any]:
    if not is_taiwan_ticker(ticker):
        record_source_health("major_holder_qfiis", "unsupported", reason="僅支援台股")
        return {"supported": False, "ticker": ticker, "message": "僅支援台股"}
    code = ticker_code(ticker)
    kind = market_kind(ticker)
    cache_key = f"major_holder_{kind}_{code}"
    cached = get_market_cache(cache_key, ttl_override=_DAY)
    if isinstance(cached, dict) and cached.get("foreign_holding_pct") is not None:
        record_source_health("major_holder_qfiis", "ok")
        return cached

    chain = build_default_chain()
    result = chain.fetch_shareholding_snapshot(ticker)
    snapshot = result.data if isinstance(result.data, dict) else {}
    if snapshot and snapshot.get("foreign_holding_pct") is not None:
        save_market_cache(cache_key, snapshot)
        record_source_health("major_holder_qfiis", "ok")
        return snapshot

    record_source_health("major_holder_qfiis", result.source_status.status, reason=result.source_status.reason)
    return {
        "supported": True,
        "ticker": ticker,
        "code": code,
        "foreign_holding_pct": None,
        "message": "外資持股資料暫不可用",
        "source": result.source_status.source_id,
    }


def holder_snapshot_to_frame(snapshot: dict[str, Any]) -> pd.DataFrame:
    if snapshot.get("foreign_holding_pct") is None:
        return pd.DataFrame()
    return pd.DataFrame([{
        "項目": "外資持股比率",
        "數值": f"{float(snapshot['foreign_holding_pct']):.2f}%",
        "來源": snapshot.get("source", ""),
    }])
