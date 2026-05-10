from __future__ import annotations

import streamlit as st

from src.repositories import user_prefs_repo
from src.repositories.holdings_repo import save_holdings

_ONBOARDING_NS = "onboarding"

MARKET_OPTIONS: list[str] = ["台股", "美股", "兩者"]
RISK_OPTIONS: list[str] = ["保守", "中性", "積極"]
ATR_MULTIPLIER_BY_RISK: dict[str, float] = {"保守": 1.5, "中性": 2.0, "積極": 2.5}
INDUSTRY_OPTIONS: list[str] = [
    "半導體", "電子零組件", "光電", "金融保險", "建材營建",
    "生技醫療", "傳統產業", "航運", "食品", "通訊網路",
    "電腦及週邊", "軟體服務",
]

_TOTAL_STEPS = 4


def is_onboarding_complete(user_id: str) -> bool:
    return bool(user_prefs_repo.get(user_id, _ONBOARDING_NS).get("completed"))


def render(user_id: str) -> None:
    st.session_state.setdefault("_onboarding_step", 1)
    st.session_state.setdefault("_onboarding_draft", {})

    step = st.session_state["_onboarding_step"]

    st.markdown("## 歡迎使用 Stock Intelligence")
    st.caption(f"步驟 {step} / {_TOTAL_STEPS} — 完成基本設定，之後可在「設定」中隨時修改。")
    st.progress(step / _TOTAL_STEPS)

    col_skip = st.columns([3, 1])[1]
    if col_skip.button("跳過初始設定", key="onboarding_skip"):
        _save_completed(user_id, skipped=True)
        _clear_draft()
        st.rerun()

    st.divider()

    if step == 1:
        _render_step_market(user_id)
    elif step == 2:
        _render_step_risk(user_id)
    elif step == 3:
        _render_step_industries(user_id)
    elif step == 4:
        _render_step_holdings(user_id)


# ── Steps ────────────────────────────────────────────────────────────────────

def _render_step_market(user_id: str) -> None:
    st.markdown("### 偏好市場")
    draft = st.session_state["_onboarding_draft"]
    current = draft.get("market", MARKET_OPTIONS[2])
    idx = MARKET_OPTIONS.index(current) if current in MARKET_OPTIONS else 2

    market = st.radio("您主要投資哪個市場？", MARKET_OPTIONS, index=idx, key="ob_market")

    _nav_buttons(back=False, on_next=lambda: _next_step({"market": market}))


def _render_step_risk(user_id: str) -> None:
    st.markdown("### 風險偏好")
    st.caption("此設定將影響策略預設的 ATR 停損倍率（保守=1.5x，中性=2.0x，積極=2.5x）。")
    draft = st.session_state["_onboarding_draft"]
    current = draft.get("risk", RISK_OPTIONS[1])
    idx = RISK_OPTIONS.index(current) if current in RISK_OPTIONS else 1

    risk = st.radio("您的投資風格？", RISK_OPTIONS, index=idx, key="ob_risk")

    _nav_buttons(on_back=_prev_step, on_next=lambda: _next_step({"risk": risk}))


def _render_step_industries(user_id: str) -> None:
    st.markdown("### 偏好產業")
    st.caption("Scanner 預設 Universe 將優先包含所選產業（可多選，亦可跳過）。")
    draft = st.session_state["_onboarding_draft"]
    saved = draft.get("industries", [])

    industries = st.multiselect(
        "偏好產業（可多選）",
        INDUSTRY_OPTIONS,
        default=[i for i in saved if i in INDUSTRY_OPTIONS],
        key="ob_industries",
    )

    _nav_buttons(on_back=_prev_step, on_next=lambda: _next_step({"industries": industries}))


def _render_step_holdings(user_id: str) -> None:
    import pandas as pd
    from src.ui.pages.settings.holdings_section import _COLUMNS, _df_to_holdings, _holdings_to_df

    st.markdown("### 持股清單")
    st.caption("輸入目前持股，Today 頁面將即時計算未實現損益（可留空，之後在「設定」中新增）。")
    draft = st.session_state["_onboarding_draft"]
    existing = draft.get("holdings_items", [])

    df_in = _holdings_to_df(existing) if existing else pd.DataFrame(columns=["ticker", "quantity", "avg_cost"])
    edited = st.data_editor(
        df_in,
        column_config=_COLUMNS,
        num_rows="dynamic",
        width="stretch",
        key="ob_holdings_editor",
    )

    def _finish() -> None:
        items = _df_to_holdings(edited)
        save_holdings(user_id, items)
        _save_completed(user_id, skipped=False)
        _clear_draft()

    _nav_buttons(on_back=_prev_step, on_next=_finish, next_label="完成設定")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nav_buttons(
    *,
    back: bool = True,
    on_back=None,
    on_next=None,
    next_label: str = "下一步",
) -> None:
    col_back, col_next = st.columns([1, 1])
    if back and on_back:
        if col_back.button("← 上一步", key="ob_back"):
            on_back()
    if col_next.button(next_label, type="primary", key="ob_next"):
        if on_next:
            on_next()


def _next_step(updates: dict) -> None:
    st.session_state["_onboarding_draft"].update(updates)
    st.session_state["_onboarding_step"] += 1
    st.rerun()


def _prev_step() -> None:
    st.session_state["_onboarding_step"] = max(1, st.session_state["_onboarding_step"] - 1)
    st.rerun()


def _save_completed(user_id: str, *, skipped: bool) -> None:
    draft = st.session_state.get("_onboarding_draft", {})
    user_prefs_repo.set(user_id, _ONBOARDING_NS, {
        "completed": True,
        "skipped": skipped,
        "market": draft.get("market", "兩者"),
        "risk": draft.get("risk", "中性"),
        "industries": draft.get("industries", []),
    })


def _clear_draft() -> None:
    st.session_state.pop("_onboarding_step", None)
    st.session_state.pop("_onboarding_draft", None)
