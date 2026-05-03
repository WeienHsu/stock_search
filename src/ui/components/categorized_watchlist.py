from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.price_fetcher import fetch_quote
from src.repositories.watchlist_category_repo import is_primary_watchlist_category, list_categories, list_items
from src.repositories.watchlist_repo import get_watchlist


def render_categorized_watchlist(user_id: str) -> str | None:
    categories = list_categories(user_id)
    if not categories:
        st.info("尚未建立分類自選")
        return None

    tabs = st.tabs([category["name"] for category in categories])
    selected_ticker: str | None = None
    for tab, category in zip(tabs, categories):
        with tab:
            items = _items_for_category(user_id, category)
            df = build_watchlist_table(items)
            if df.empty:
                st.caption("此分類尚無股票")
                continue
            event = st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                key=f"categorized_watchlist_{category['id']}",
            )
            selected = getattr(event, "selection", None)
            rows = getattr(selected, "rows", []) if selected is not None else []
            if rows:
                selected_ticker = str(df.iloc[int(rows[0])]["代碼"])

    if selected_ticker:
        st.session_state["workstation_active_ticker"] = selected_ticker
    return selected_ticker


def _items_for_category(user_id: str, category: dict) -> list[dict]:
    if is_primary_watchlist_category(category):
        return get_watchlist(user_id)
    return list_items(user_id, category["id"])


def build_watchlist_table(items: list[dict]) -> pd.DataFrame:
    rows = []
    for item in items:
        ticker = str(item["ticker"]).upper()
        quote = _quote_summary(ticker)
        rows.append({
            "代碼": ticker,
            "名稱": item.get("name", ""),
            "成交": quote["close"],
            "漲跌": quote["change"],
            "漲幅%": quote["change_pct"],
            "總量": quote["volume"],
            "內外盤比": "—",
            "PE": "—",
        })
    return pd.DataFrame(rows)


def _quote_summary(ticker: str) -> dict:
    try:
        df = fetch_quote(ticker)
    except Exception:
        df = pd.DataFrame()
    if df.empty or "close" not in df.columns:
        return {"close": "—", "change": "—", "change_pct": "—", "volume": "—"}

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    close = float(latest["close"])
    prev_close = float(prev["close"]) if float(prev["close"]) else close
    change = close - prev_close
    change_pct = change / prev_close * 100 if prev_close else 0.0
    volume = float(latest["volume"]) if "volume" in df.columns else 0.0
    return {
        "close": round(close, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "volume": int(volume),
    }
