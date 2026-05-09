import streamlit as st
import pandas as pd

from src.core.sorting import sort_watchlist_items
from src.core.strategy_registry import list_strategies
from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist
from src.ui.components.data_table import ColumnSpec, render_data_table
from src.ui.components.empty_state import render_empty_state
from src.ui.nav.page_keys import DASHBOARD, LABEL_BY_KEY, SETTINGS
from src.ui.utils.styler import style_pct_change

import src.strategies.strategy_d   # ensure registration
import src.strategies.strategy_kd  # ensure registration

_STRATEGY_LABELS = {
    "strategy_d":  "Strategy D（MACD + KD）",
    "strategy_kd": "Strategy KD（黃金 / 死亡交叉）",
}

_SORT_OPTIONS = {
    "訊號優先": "__signal_priority__",
    "代號": "ticker",
    "名稱": "name",
    "現價": "current_close",
    "日漲跌": "daily_change_pct",
    "買進狀態": "buy_status",
    "最近買進日": "last_buy_date",
    "賣出狀態": "sell_status",
    "最近賣出日": "last_sell_date",
    "多頭排列": "ma_bullish_score",
    "趨勢": "trend",
}


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 市場掃描器")

    items = sort_watchlist_items(get_watchlist(user_id))
    if not items:
        if render_empty_state(
            "search",
            "自選清單為空",
            "請先到設定頁新增股票，再回來掃描訊號。",
            action_label="前往設定",
            action_key="scanner_empty_go_settings",
        ):
            _queue_page_nav(SETTINGS)
            st.rerun()
        return

    col_strat, col_btn = st.columns([3, 1], vertical_alignment="bottom")
    with col_strat:
        available = list_strategies()
        strategy_id = st.selectbox(
            "掃描策略",
            options=available,
            index=0,
            format_func=lambda x: _STRATEGY_LABELS.get(x, x),
            key="scanner_strategy",
        )
    with col_btn:
        run_scan = st.button("開始掃描", width="stretch")

    tickers_display = ", ".join(i["ticker"] for i in items)
    st.caption(f"自選清單：{tickers_display}")

    strategy_params = cfg.get(strategy_id, {})
    strategy_label = _STRATEGY_LABELS.get(strategy_id, strategy_id)

    if run_scan:
        with st.spinner(f"使用 {strategy_label} 掃描中，請稍候…"):
            result_df = scan_watchlist(items, strategy_id=strategy_id, strategy_params=strategy_params)
        st.session_state["scanner_result_df"] = result_df
        st.session_state["scanner_result_strategy_id"] = strategy_id
        st.session_state["scanner_result_strategy_label"] = strategy_label
    else:
        result_df = st.session_state.get("scanner_result_df")
        if result_df is None:
            render_empty_state("search", "尚未開始掃描", "選擇策略後點擊「開始掃描」。")
            return
        stored_strategy_id = st.session_state.get("scanner_result_strategy_id")
        if stored_strategy_id != strategy_id:
            render_empty_state("settings", "掃描策略已變更", "請重新點擊「開始掃描」產生新結果。")
            return
        strategy_label = st.session_state.get("scanner_result_strategy_label", strategy_label)

    if result_df.empty:
        render_empty_state("data", "掃描無結果", f"{strategy_label} 目前沒有觸發的買進或賣出訊號。")
        return

    result_df = _sort_results(result_df)

    triggered_buy  = result_df[result_df["buy_signal"]  == True]
    triggered_sell = result_df[result_df["sell_signal"] == True]

    if not triggered_buy.empty:
        st.success(f"**{len(triggered_buy)}** 檔觸發買進訊號（{strategy_label}）")
    if not triggered_sell.empty:
        st.warning(f"**{len(triggered_sell)}** 檔觸發賣出訊號（{strategy_label}）")

    _render_result_table(result_df)


def _sort_results(result_df: pd.DataFrame) -> pd.DataFrame:
    col_sort, col_dir = st.columns([2, 1])
    with col_sort:
        sort_label = st.selectbox(
            "排序欄位",
            options=list(_SORT_OPTIONS.keys()),
            index=0,
            key="scanner_sort_field",
        )
    with col_dir:
        descending = st.toggle("由大到小", value=True, key="scanner_sort_desc")

    sort_col = _SORT_OPTIONS[sort_label]
    if sort_col == "__signal_priority__":
        return result_df.sort_values(
            ["buy_signal", "sell_signal", "ticker"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    sorted_df = result_df.copy()
    if sort_col in {"last_buy_date", "last_sell_date"}:
        sorted_df[f"__{sort_col}_sort"] = pd.to_datetime(
            sorted_df[sort_col].replace("—", pd.NA),
            errors="coerce",
        )
        return sorted_df.sort_values(
            [f"__{sort_col}_sort", "ticker"],
            ascending=[not descending, True],
            na_position="last",
        ).drop(columns=[f"__{sort_col}_sort"]).reset_index(drop=True)

    if sort_col not in sorted_df.columns:
        sorted_df[sort_col] = pd.NA

    return sorted_df.sort_values(
        [sort_col, "ticker"],
        ascending=[not descending, True],
        na_position="last",
    ).reset_index(drop=True)


def _render_result_table(result_df: pd.DataFrame) -> None:
    view = result_df.copy()
    view["month_above_quarter_label"] = view["month_above_quarter"].map(lambda value: "是" if bool(value) else "否")
    view["in_support_zone_label"] = view["in_support_zone"].map(lambda value: "是" if bool(value) else "—")
    view["ma_bullish_score"] = pd.to_numeric(view["ma_bullish_score"], errors="coerce").fillna(0).astype(int)
    view["daily_change_pct"] = pd.to_numeric(view.get("daily_change_pct"), errors="coerce")
    view["poc_distance_pct"] = pd.to_numeric(view["poc_distance_pct"], errors="coerce")
    schema = _result_table_schema()
    visible_keys = [column.key for column in schema if column.key in view.columns]
    styled_view = style_pct_change(view[visible_keys].copy(), ["daily_change_pct"])

    event = render_data_table(
        view,
        schema,
        key="scanner_results_table",
        on_select=True,
        styled_df=styled_view,
    )
    if event.selection.rows:
        ticker = str(view.iloc[event.selection.rows[0]]["ticker"])
        _queue_dashboard_nav(ticker)
        st.rerun()


def _queue_dashboard_nav(ticker: str) -> None:
    st.session_state["_pending_nav_page"] = LABEL_BY_KEY[DASHBOARD]
    st.session_state["_pending_ticker"] = ticker


def _queue_page_nav(page_key: str) -> None:
    st.session_state["_pending_nav_page"] = LABEL_BY_KEY[page_key]


def _result_table_schema() -> list[ColumnSpec]:
    return [
        ColumnSpec("ticker", "代號", width="small"),
        ColumnSpec("name", "名稱", width="medium"),
        ColumnSpec("current_close", "現價", type="number", format="%.2f", width="small"),
        ColumnSpec("daily_change_pct", "日漲跌", type="pct", format="%+.2f%%", width="small"),
        ColumnSpec("buy_status", "買進狀態", width="medium"),
        ColumnSpec("last_buy_date", "最近買進日", width="small"),
        ColumnSpec("sell_status", "賣出狀態", width="medium"),
        ColumnSpec("last_sell_date", "最近賣出日", width="small"),
        ColumnSpec("ma_bullish_score", "多頭排列", type="progress", min_value=0, max_value=4, format="%d/4", width="small"),
        ColumnSpec("month_above_quarter_label", "月>季", width="small"),
        ColumnSpec("trend", "趨勢", width="small"),
        ColumnSpec("poc_distance_pct", "距POC", type="pct", format="%+.1f%%", width="small"),
        ColumnSpec("in_support_zone_label", "支撐帶", width="small"),
    ]
