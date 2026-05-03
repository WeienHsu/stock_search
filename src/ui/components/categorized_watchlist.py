from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.ticker_utils import normalize_ticker
from src.data.price_fetcher import fetch_quote
from src.repositories.watchlist_category_repo import is_primary_watchlist_category, list_categories, list_items
from src.repositories.watchlist_repo import get_watchlist


def render_categorized_watchlist(user_id: str) -> str | None:
    categories = list_categories(user_id)
    if not categories:
        st.info("尚未建立分類自選")
        return None

    selected_from_picker = _render_ticker_picker(user_id, categories)
    selected_from_input = _render_direct_ticker_input()
    selected_ticker = selected_from_input or selected_from_picker

    tabs = st.tabs([category["name"] for category in categories])
    for tab, category in zip(tabs, categories):
        with tab:
            items = _items_for_category(user_id, category)
            df = build_watchlist_table(items, include_quotes=False)
            if df.empty:
                st.caption("此分類尚無股票")
                continue
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                key=f"categorized_watchlist_{category['id']}",
            )

    if selected_ticker:
        st.session_state["workstation_active_ticker"] = selected_ticker
    return selected_ticker


def _items_for_category(user_id: str, category: dict) -> list[dict]:
    if is_primary_watchlist_category(category):
        return get_watchlist(user_id)
    return list_items(user_id, category["id"])


def build_watchlist_table(items: list[dict], *, include_quotes: bool = True) -> pd.DataFrame:
    rows = []
    for item in items:
        ticker = str(item["ticker"]).upper()
        quote = _quote_summary(ticker) if include_quotes else {"close": "—", "change": "—", "change_pct": "—", "volume": "—"}
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


def _render_ticker_picker(user_id: str, categories: list[dict]) -> str | None:
    options = _picker_options(user_id, categories)
    if not options:
        return None
    active = str(st.session_state.get("workstation_active_ticker") or "").upper()
    tickers = [option["ticker"] for option in options]
    if active and active not in tickers:
        options.insert(0, {"ticker": active, "name": "", "category": "目前"})
        tickers.insert(0, active)
    index = tickers.index(active) if active in tickers else 0
    selected = st.selectbox(
        "選擇股票",
        options=tickers,
        index=index,
        format_func=lambda ticker: _picker_label(ticker, options),
        key=f"workstation_category_picker_{active or 'default'}",
    )
    return str(selected).upper() if selected else None


def _render_direct_ticker_input() -> str | None:
    col_ticker, col_apply = st.columns([3, 1])
    raw_ticker = col_ticker.text_input(
        "直接輸入代碼",
        placeholder="6491.TW / 6491",
        key="workstation_direct_ticker",
    )
    if col_apply.button("套用", key="workstation_direct_ticker_apply", use_container_width=True):
        ticker = normalize_ticker(raw_ticker)
        if ticker:
            return ticker
        st.warning("請輸入股票代碼")
    return None


def _picker_options(user_id: str, categories: list[dict]) -> list[dict]:
    seen = set()
    options = []
    for category in categories:
        category_name = str(category.get("name") or "")
        for item in _items_for_category(user_id, category):
            ticker = str(item.get("ticker") or "").upper()
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            options.append({
                "ticker": ticker,
                "name": item.get("name", ""),
                "category": category_name,
            })
    return options


def _picker_label(ticker: str, options: list[dict]) -> str:
    for option in options:
        if option["ticker"] == ticker:
            name = str(option.get("name") or "")
            category = str(option.get("category") or "")
            parts = [ticker]
            if name:
                parts.append(name)
            if category:
                parts.append(f"({category})")
            return " ".join(parts)
    return ticker


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
