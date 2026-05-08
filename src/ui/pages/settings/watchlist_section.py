from __future__ import annotations

import streamlit as st

from src.core.sorting import sort_watchlist_items
from src.data.ticker_utils import normalize_ticker
from src.repositories.watchlist_repo import add_ticker, get_watchlist, remove_ticker


def render_watchlist_section(user_id: str) -> None:
    from src.repositories.watchlist_category_repo import (
        add_item,
        create_category,
        delete_category,
        delete_item,
        is_primary_watchlist_category,
        list_categories,
        list_items,
    )

    st.markdown("### 綜合看盤分類")
    st.caption("「自選清單」是掃描器、每日掃描與週報使用的主清單；其他分類只管理 ticker 分組。")
    categories = list_categories(user_id)

    col_name, col_add = st.columns([3, 1], vertical_alignment="bottom")
    category_name = col_name.text_input("新增分類", key="new_watchlist_category")
    if col_add.button("新增分類"):
        if category_name.strip():
            create_category(user_id, category_name.strip())
            st.rerun()
        st.warning("請輸入分類名稱")

    if not categories:
        st.caption("尚無分類")
        return

    selected_category = st.selectbox(
        "選擇分類",
        categories,
        format_func=lambda item: item["name"],
        key="watchlist_category_select",
    )
    category_id = selected_category["id"]
    if is_primary_watchlist_category(selected_category):
        _render_primary_watchlist_settings(user_id)
        return

    items = list_items(user_id, category_id)
    if items:
        for item in items:
            col_ticker, col_name, col_delete = st.columns([1.2, 2.3, 0.8], vertical_alignment="center")
            col_ticker.markdown(f"**{item['ticker']}**")
            col_name.markdown(item.get("name", "") or "—")
            if col_delete.button("刪除", key=f"delete_category_item_{item['id']}"):
                delete_item(user_id, item["id"])
                st.rerun()
    else:
        st.caption("此分類尚無股票")

    col_ticker, col_item_name, col_add_item = st.columns([1.4, 2.0, 0.8], vertical_alignment="bottom")
    new_item_ticker = col_ticker.text_input("代碼", key=f"new_item_ticker_{category_id}", placeholder="2330.TW")
    new_item_name = col_item_name.text_input("名稱（選填）", key=f"new_item_name_{category_id}")
    if col_add_item.button("新增", key=f"add_item_{category_id}"):
        if new_item_ticker.strip():
            add_item(user_id, category_id, normalize_ticker(new_item_ticker), new_item_name)
            st.rerun()
        st.warning("請輸入股票代碼")

    if len(categories) > 1 and st.button("刪除此分類", key=f"delete_category_{category_id}"):
        delete_category(user_id, category_id)
        st.rerun()


def _render_primary_watchlist_settings(user_id: str) -> None:
    items = sort_watchlist_items(get_watchlist(user_id))

    if items:
        for item in items:
            col1, col2 = st.columns([4, 1], vertical_alignment="center")
            col1.markdown(f"**{item['ticker']}** &nbsp; {item.get('name', '')}")
            if col2.button("移除", key=f"rm_primary_watchlist_{item['ticker']}"):
                remove_ticker(user_id, item["ticker"])
                st.rerun()
    else:
        st.caption("自選清單為空")

    col_t, col_n, col_b = st.columns([2, 2, 1], vertical_alignment="bottom")
    new_ticker = col_t.text_input("新增 ticker", placeholder="2330.TW", key="primary_watchlist_new_ticker")
    new_name = col_n.text_input("名稱（選填）", key="primary_watchlist_new_name")
    if col_b.button("新增", key="primary_watchlist_add"):
        if new_ticker.strip():
            add_ticker(user_id, normalize_ticker(new_ticker), new_name)
            st.rerun()
        st.warning("請輸入股票代碼")
