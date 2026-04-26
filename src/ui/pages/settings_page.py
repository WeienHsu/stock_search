import streamlit as st

from src.repositories.watchlist_repo import add_ticker, get_watchlist, remove_ticker
from src.repositories.preferences_repo import get_preferences, save_preferences
from src.data.ticker_utils import normalize_ticker


def render(user_id: str) -> None:
    st.markdown("## 設定")

    # ── Watchlist management ──
    st.markdown("### 自選清單")
    items = get_watchlist(user_id)

    if items:
        for item in items:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"**{item['ticker']}** &nbsp; {item.get('name', '')}")
            if col2.button("移除", key=f"rm_{item['ticker']}"):
                remove_ticker(user_id, item["ticker"])
                st.rerun()
    else:
        st.caption("自選清單為空")

    st.markdown("---")
    col_t, col_n, col_b = st.columns([2, 2, 1])
    new_ticker = col_t.text_input("新增 ticker", placeholder="2330.TW")
    new_name   = col_n.text_input("名稱（選填）")
    if col_b.button("新增"):
        if new_ticker:
            add_ticker(user_id, normalize_ticker(new_ticker), new_name)
            st.rerun()

    # ── Preferences ──
    st.markdown("---")
    st.markdown("### 偏好設定")
    prefs = get_preferences(user_id)

    default_period = st.selectbox("預設時間區間", ["1D","5D","1M","6M","1Y"],
                                  index=["1D","5D","1M","6M","1Y"].index(prefs.get("default_period","6M")))

    if st.button("儲存偏好"):
        prefs["default_period"] = default_period
        save_preferences(user_id, prefs)
        st.success("已儲存")
