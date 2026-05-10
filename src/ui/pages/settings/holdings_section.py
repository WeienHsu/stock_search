from __future__ import annotations

import pandas as pd
import streamlit as st

from src.repositories.holdings_repo import get_holdings, save_holdings


_COLUMNS = {
    "ticker": st.column_config.TextColumn("股票代號", help="例如：2330.TW、TSLA", required=True),
    "quantity": st.column_config.NumberColumn("股數", min_value=1, step=1, required=True),
    "avg_cost": st.column_config.NumberColumn("平均成本", min_value=0.01, format="%.2f", required=True),
}


def render_holdings_section(user_id: str) -> None:
    st.markdown("### 持股管理")
    st.caption("輸入持股後，Today 頁面將顯示即時未實現損益。")

    current = get_holdings(user_id)
    df_in = _holdings_to_df(current)

    edited = st.data_editor(
        df_in,
        column_config=_COLUMNS,
        num_rows="dynamic",
        use_container_width=True,
        key="holdings_editor",
    )

    if st.button("儲存持股", type="primary"):
        items = _df_to_holdings(edited)
        save_holdings(user_id, items)
        st.success(f"已儲存 {len(items)} 筆持股。")
        st.rerun()


def _holdings_to_df(items: list[dict]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame(columns=["ticker", "quantity", "avg_cost"])
    return pd.DataFrame(items)[["ticker", "quantity", "avg_cost"]]


def _df_to_holdings(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        try:
            quantity = float(row["quantity"])
            avg_cost = float(row["avg_cost"])
        except (KeyError, TypeError, ValueError):
            continue
        if quantity > 0 and avg_cost > 0:
            records.append({"ticker": ticker, "quantity": quantity, "avg_cost": avg_cost})
    return records
