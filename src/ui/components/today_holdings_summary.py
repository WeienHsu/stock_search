from __future__ import annotations

from typing import Any

import streamlit as st

from src.repositories.risk_settings_repo import get_risk_settings
from src.ui.components.empty_state import render_empty_state
from src.ui.components.kpi_card import render_kpi_card


def render_today_holdings_summary(user_id: str) -> None:
    summary = build_holdings_summary(get_risk_settings(user_id).get("holdings"))
    if summary["count"] == 0:
        render_empty_state("data", "尚未設定持股", "目前沒有可計算的持股資料。可先在風控設定中建立資料結構。")
        return

    col_count, col_value, col_pnl = st.columns(3)
    with col_count:
        render_kpi_card("持股檔數", f"{summary['count']:,}")
    with col_value:
        render_kpi_card("持股市值", _money(summary["market_value"]))
    with col_pnl:
        direction = "up" if summary["unrealized_pnl"] > 0 else "down" if summary["unrealized_pnl"] < 0 else "flat"
        render_kpi_card(
            "未實現損益",
            _money(summary["unrealized_pnl"]),
            delta=f"{summary['unrealized_pnl_pct']:+.2f}%",
            delta_direction=direction,
        )


def build_holdings_summary(holdings: Any) -> dict[str, float | int]:
    if not isinstance(holdings, list):
        return _empty_summary()

    total_cost = 0.0
    market_value = 0.0
    count = 0
    for holding in holdings:
        if not isinstance(holding, dict):
            continue
        quantity = _number(holding, "quantity", "shares", "units")
        avg_cost = _number(holding, "avg_cost", "average_cost", "cost_basis", "cost")
        current_price = _number(holding, "current_price", "market_price", "last_price", "price")
        if quantity is None or avg_cost is None or current_price is None:
            continue
        total_cost += quantity * avg_cost
        market_value += quantity * current_price
        count += 1

    if count == 0:
        return _empty_summary()

    unrealized_pnl = market_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost else 0.0
    return {
        "count": count,
        "total_cost": round(total_cost, 2),
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
    }


def _empty_summary() -> dict[str, float | int]:
    return {
        "count": 0,
        "total_cost": 0.0,
        "market_value": 0.0,
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
    }


def _number(data: dict, *keys: str) -> float | None:
    for key in keys:
        value = data.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _money(value: float | int) -> str:
    return f"{float(value):,.0f}"
