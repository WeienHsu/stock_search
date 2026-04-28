import streamlit as st

from src.core.sorting import sort_watchlist_items
from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 市場掃描器")
    st.caption("掃描自選清單，標示當前 Strategy D 買進 / 賣出訊號狀態")

    items = sort_watchlist_items(get_watchlist(user_id))
    if not items:
        st.info("自選清單為空，請先至「設定」頁面新增股票。")
        return

    tickers_display = ", ".join(i["ticker"] for i in items)
    st.markdown(f"**自選清單**：{tickers_display}")

    if st.button("開始掃描", use_container_width=False):
        with st.spinner("掃描中，請稍候…"):
            result_df = scan_watchlist(items, cfg["strategy_d"])

        if result_df.empty:
            st.warning("掃描無結果")
            return

        # Sort: buy triggered first, then sell triggered, then others
        result_df = result_df.sort_values(
            ["buy_signal", "sell_signal"], ascending=[False, False]
        ).reset_index(drop=True)

        triggered_buy  = result_df[result_df["buy_signal"]  == True]
        triggered_sell = result_df[result_df["sell_signal"] == True]

        if not triggered_buy.empty:
            st.success(f"**{len(triggered_buy)}** 檔觸發買進訊號")
        if not triggered_sell.empty:
            st.warning(f"**{len(triggered_sell)}** 檔觸發賣出訊號")

        display_cols = ["ticker", "name", "current_close",
                        "buy_status", "last_buy_date",
                        "sell_status", "last_sell_date"]
        col_names    = ["代號", "名稱", "現價",
                        "買進狀態", "最近買進日",
                        "賣出狀態", "最近賣出日"]

        show_df = result_df[display_cols].copy()
        show_df.columns = col_names

        table_height = max(300, min(36 * len(show_df) + 38, 900))
        st.dataframe(show_df, use_container_width=True, hide_index=True, height=table_height)
    else:
        st.info("點擊「開始掃描」執行")
