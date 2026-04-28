import json
from pathlib import Path

import streamlit as st

import finnhub
from src.core.finnhub_mode import current_mode
from src.core.sorting import sort_watchlist_items
from src.data.ticker_utils import normalize_ticker
from src.repositories.preferences_repo import get_preferences, save_preferences
from src.repositories.user_secrets_repo import clear_secret, get_secret, has_secret, set_secret
from src.repositories.watchlist_repo import add_ticker, get_watchlist, remove_ticker

_SETTINGS_PATH = Path(__file__).parents[3] / "config" / "default_settings.json"


def _load_defaults() -> dict:
    with open(_SETTINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render(user_id: str) -> None:
    st.markdown("## 設定")

    # ── Watchlist management ──
    st.markdown("### 自選清單")
    items = sort_watchlist_items(get_watchlist(user_id))

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
    defaults = _load_defaults()

    periods = defaults["ui"]["available_periods"]
    _saved_default = prefs.get("default_period", "6M")
    _default_idx = periods.index(_saved_default) if _saved_default in periods else periods.index("6M")
    default_period = st.selectbox(
        "預設快速縮放", periods,
        index=_default_idx,
    )

    if st.button("儲存偏好"):
        prefs["default_period"] = default_period
        save_preferences(user_id, prefs)
        st.success("已儲存")

    # ── Strategy D default params ──
    st.markdown("---")
    st.markdown("### Strategy D 參數預設值")
    st.caption("設定後，側邊欄的參數滑桿將以此作為預設值。")

    sd = defaults["strategy_d"]
    col1, col2 = st.columns(2)
    with col1:
        kd_window_new = st.slider(
            "KD 回看視窗", 5, 20, int(prefs.get("kd_window", sd["kd_window"])),
            key="settings_kd_window",
        )
        n_bars_new = st.slider(
            "MACD 收斂根數", 1, 7, int(prefs.get("n_bars", sd["n_bars"])),
            key="settings_n_bars",
        )
    with col2:
        recovery_new = st.slider(
            "回彈比例", 0.3, 0.9, float(prefs.get("recovery_pct", sd["recovery_pct"])),
            step=0.05, key="settings_recovery",
        )
        kd_thresh_new = st.slider(
            "KD 閾值", 10, 35, int(prefs.get("kd_k_threshold", sd["kd_k_threshold"])),
            key="settings_kd_thresh",
        )

    if st.button("儲存 Strategy D 參數"):
        prefs.update({
            "kd_window": kd_window_new,
            "n_bars": n_bars_new,
            "recovery_pct": recovery_new,
            "kd_k_threshold": kd_thresh_new,
        })
        save_preferences(user_id, prefs)
        st.success("已儲存 Strategy D 參數，側邊欄下次展開時將使用新預設值")

    # ── Finnhub API Key ──
    st.markdown("---")
    st.markdown("### 市場情緒 API")
    mode = current_mode()

    if mode == "global":
        st.info("目前由系統管理者統一設定 Finnhub API key，無需個別配置。")
    else:
        key_set = has_secret(user_id, "finnhub_api_key")
        if key_set:
            st.success("API key 已設定 ✓")
        else:
            st.warning("尚未設定 Finnhub API key，Dashboard 的市場情緒功能無法使用。")

        new_key = st.text_input(
            "輸入新 API key（儲存後無法查看原始值）",
            type="password",
            key="finnhub_key_input",
            placeholder="留空表示不更換",
        )

        col_save, col_test, col_clear = st.columns(3)

        if col_save.button("儲存金鑰"):
            if new_key.strip():
                set_secret(user_id, "finnhub_api_key", new_key.strip())
                st.success("已儲存")
                st.rerun()
            else:
                st.warning("請先輸入 API key")

        if col_test.button("測試連線"):
            test_key = new_key.strip() or get_secret(user_id, "finnhub_api_key")
            if not test_key:
                st.error("尚未設定 API key，無法測試")
            else:
                try:
                    finnhub.Client(api_key=test_key).general_news("general", min_id=0)
                    st.success("✓ 連線成功")
                except Exception as e:
                    st.error(f"✗ 連線失敗：{e}")

        if key_set and col_clear.button("移除金鑰"):
            clear_secret(user_id, "finnhub_api_key")
            st.success("已移除")
            st.rerun()
