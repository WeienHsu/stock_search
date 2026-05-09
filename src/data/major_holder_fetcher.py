from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.data.chip_data_sources import build_default_chain
from src.data.chip_utils import is_taiwan_ticker, market_kind, ticker_code
from src.data.dynamic_ttl import get_ttl
from src.repositories.market_data_cache_repo import get_market_cache, save_market_cache
from src.repositories.source_health_repo import record_source_health

_DAY = 24 * 3600


@st.cache_data(ttl=get_ttl(600), show_spinner=False)
def fetch_major_holder_snapshot(ticker: str) -> dict[str, Any]:
    if not is_taiwan_ticker(ticker):
        record_source_health("major_holder_qfiis", "unsupported", reason="僅支援台股")
        return {"supported": False, "ticker": ticker, "message": "僅支援台股"}
    code = ticker_code(ticker)
    kind = market_kind(ticker)
    cache_key = f"major_holder_v2_{kind}_{code}"
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
    source = snapshot.get("source", "")
    rows: list[dict[str, Any]] = []

    pct = float(snapshot["foreign_holding_pct"])
    rows.append({"項目": "外資持股比率", "數值": f"{pct:.2f}%", "來源": source})

    change = snapshot.get("foreign_holding_change_pp")
    if change is not None:
        rows.append({"項目": "近期變動", "數值": f"{float(change):+.2f} pp", "來源": source})

    upper = snapshot.get("foreign_upper_limit_pct")
    if upper is not None:
        rows.append({"項目": "外資投資上限", "數值": f"{float(upper):.2f}%", "來源": source})

    issued = snapshot.get("shares_issued")
    foreign_shares = snapshot.get("foreign_holding_shares")
    if issued and foreign_shares is not None:
        rows.append({
            "項目": "外資持股張數",
            "數值": _format_lots(foreign_shares),
            "來源": source,
        })
        rows.append({
            "項目": "已發行張數",
            "數值": _format_lots(issued),
            "來源": source,
        })

    snapshot_date = snapshot.get("date")
    if snapshot_date:
        rows.append({"項目": "資料日期", "數值": str(snapshot_date), "來源": source})

    return pd.DataFrame(rows)


def holder_history_to_frame(snapshot: dict[str, Any]) -> pd.DataFrame:
    history = snapshot.get("history") or []
    if not isinstance(history, list) or not history:
        return pd.DataFrame()
    df = pd.DataFrame(history)
    if df.empty or "date" not in df.columns or "foreign_holding_pct" not in df.columns:
        return pd.DataFrame()
    df = df.dropna(subset=["foreign_holding_pct"]).copy()
    df["date"] = df["date"].astype(str)
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _format_lots(shares: Any) -> str:
    try:
        lots = float(shares) / 1000
    except (TypeError, ValueError):
        return "—"
    if abs(lots) >= 10_000:
        return f"{lots / 10_000:,.2f} 萬張"
    return f"{lots:,.0f} 張"
