import streamlit as st

from src.repositories.watchlist_repo import get_watchlist
from src.scanner.watchlist_scanner import scan_watchlist


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 市場掃描器")
    st.caption("掃描自選清單，標示當前 Strategy D 訊號狀態")

    items = get_watchlist(user_id)
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

        # Sort: triggered first
        result_df = result_df.sort_values("signal", ascending=False).reset_index(drop=True)

        # Highlight triggered rows
        triggered = result_df[result_df["signal"] == True]
        others    = result_df[result_df["signal"] == False]

        if not triggered.empty:
            st.success(f"**{len(triggered)}** 檔觸發 Strategy D 訊號")

        display_cols = ["status", "ticker", "name", "current_close", "last_signal_date"]
        col_names    = ["狀態", "代號", "名稱", "現價", "最近訊號日"]

        show_df = result_df[display_cols].copy()
        show_df.columns = col_names
        st.dataframe(show_df, use_container_width=True, hide_index=True)
    else:
        st.info("點擊「開始掃描」執行")
