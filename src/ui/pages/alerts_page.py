from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.data.ticker_utils import normalize_ticker
from src.repositories import alert_repo
from src.repositories.inbox_repo import list_messages, mark_read, unread_count
from src.repositories.scheduler_run_repo import list_runs

_DIRECTION_LABELS = {"高於或等於": "above", "低於或等於": "below"}
_DIRECTION_TEXT = {"above": ">=", "below": "<="}


def render(user_id: str) -> None:
    st.markdown("## 警示")

    tab_alerts, tab_inbox, tab_runs = st.tabs(["價格警示", "Inbox", "排程紀錄"])
    with tab_alerts:
        _render_price_alerts(user_id)
    with tab_inbox:
        _render_inbox(user_id)
    with tab_runs:
        _render_scheduler_runs()


def _render_price_alerts(user_id: str) -> None:
    st.markdown("### 新增價格警示")
    col_ticker, col_direction, col_threshold, col_button = st.columns([2, 2, 2, 1], vertical_alignment="bottom")
    ticker = col_ticker.text_input("Ticker", placeholder="TSLA / 2330.TW", key="alert_ticker")
    direction_label = col_direction.selectbox("條件", list(_DIRECTION_LABELS), key="alert_direction")
    threshold = col_threshold.number_input("價格", min_value=0.0, value=0.0, step=1.0, key="alert_threshold")
    if col_button.button("新增", width="stretch"):
        normalized = normalize_ticker(ticker)
        if not normalized or threshold <= 0:
            st.warning("請輸入 ticker 與大於 0 的價格")
        else:
            alert_repo.create_price_alert(
                user_id,
                normalized,
                _DIRECTION_LABELS[direction_label],
                threshold,
            )
            st.success("已新增價格警示")
            st.rerun()

    st.divider()
    st.markdown("### 既有警示")
    alerts = alert_repo.list_alerts(user_id)
    if not alerts:
        st.caption("尚無警示")
        return

    header = st.columns([1.3, 1.0, 1.2, 1.0, 1.5, 1.0, 1.0])
    for col, label in zip(header, ["Ticker", "條件", "價格", "狀態", "觸發時間", "啟用", "刪除"]):
        col.markdown(f"**{label}**")

    for alert in alerts:
        cols = st.columns([1.3, 1.0, 1.2, 1.0, 1.5, 1.0, 1.0])
        cols[0].markdown(f"**{alert['ticker']}**")
        cols[1].markdown(_DIRECTION_TEXT.get(alert["direction"], alert["direction"]))
        cols[2].markdown(f"{float(alert['threshold']):.2f}")
        cols[3].markdown("已觸發" if alert.get("triggered_at") else "等待中")
        cols[4].markdown(_format_ts(alert.get("triggered_at")))
        enabled = cols[5].toggle(
            "啟用",
            value=bool(alert["enabled"]),
            label_visibility="collapsed",
            key=f"alert_enabled_{alert['id']}",
        )
        if enabled != bool(alert["enabled"]):
            alert_repo.set_alert_enabled(alert["id"], enabled)
            st.rerun()
        if cols[6].button("刪除", key=f"delete_alert_{alert['id']}"):
            alert_repo.delete_alert(alert["id"])
            st.rerun()


def _render_inbox(user_id: str) -> None:
    count = unread_count(user_id)
    st.caption(f"未讀：{count}")
    messages = list_messages(user_id, limit=50)
    if not messages:
        st.info("Inbox 目前沒有訊息")
        return

    for message in messages:
        marker = "●" if message.get("read_at") is None else "○"
        with st.expander(f"{marker} {message['subject']} · {_format_ts(message['created_at'])}"):
            st.write(message["body"])
            if message.get("read_at") is None and st.button("標為已讀", key=f"read_{message['id']}"):
                mark_read(message["id"])
                st.rerun()


def _render_scheduler_runs() -> None:
    runs = list_runs(limit=30)
    if not runs:
        st.info("尚無排程執行紀錄")
        return
    for run in runs:
        st.markdown(
            f"**{run['job_name']}** · {run['status']} · "
            f"{_format_ts(run['started_at'])}"
        )
        if run.get("error"):
            st.code(run["error"])


def _format_ts(value: float | None) -> str:
    if not value:
        return "—"
    return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
