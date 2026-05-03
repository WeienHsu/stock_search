import json
import os
from pathlib import Path

import streamlit as st

import finnhub
from src.core.finnhub_mode import current_mode
from src.core.sorting import sort_watchlist_items
from src.data.ticker_utils import normalize_ticker
from src.notifications import send_notification
from src.repositories.notification_settings_repo import get_settings, save_settings
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

    _render_watchlist_category_settings(user_id)

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
        buy_kd_window_new = st.slider(
            "買進 KD 回看視窗", 1, 10, int(prefs.get("buy_kd_window", prefs.get("kd_window", sd["buy_kd_window"]))),
            key="settings_buy_kd_window",
        )
        buy_n_bars_new = st.slider(
            "買進 MACD 收斂根數", 3, 10, int(prefs.get("buy_n_bars", prefs.get("n_bars", sd["buy_n_bars"]))),
            key="settings_buy_n_bars",
        )
        buy_max_viol_new = st.slider(
            "買進 MACD 容忍違反根數", 0, 3,
            int(prefs.get("buy_max_violations", prefs.get("max_violations", sd["buy_max_violations"]))),
            key="settings_buy_max_violations",
            help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）",
        )
        buy_recovery_new = st.slider(
            "買進回彈比例", 0.3, 0.9,
            float(prefs.get("buy_recovery_pct", prefs.get("recovery_pct", sd["buy_recovery_pct"]))),
            step=0.05, key="settings_buy_recovery",
        )
        buy_kd_thresh_new = st.slider(
            "買進 KD 閾值", 10, 35, int(prefs.get("buy_kd_k_threshold", prefs.get("kd_k_threshold", sd["buy_kd_k_threshold"]))),
            key="settings_buy_kd_thresh",
        )
        buy_lookback_new = st.slider(
            "買進 MACD 峰谷回看根數", 10, 40,
            int(prefs.get("buy_lookback_bars", prefs.get("lookback_bars", sd["buy_lookback_bars"]))),
            key="settings_buy_lookback_bars",
        )
    with col2:
        sell_kd_window_new = st.slider(
            "賣出 KD 回看視窗", 1, 10, int(prefs.get("sell_kd_window", prefs.get("kd_window", sd["sell_kd_window"]))),
            key="settings_sell_kd_window",
        )
        sell_n_bars_new = st.slider(
            "賣出 MACD 收斂根數", 3, 10, int(prefs.get("sell_n_bars", prefs.get("n_bars", sd["sell_n_bars"]))),
            key="settings_sell_n_bars",
        )
        sell_max_viol_new = st.slider(
            "賣出 MACD 容忍違反根數", 0, 3,
            int(prefs.get("sell_max_violations", prefs.get("max_violations", sd["sell_max_violations"]))),
            key="settings_sell_max_violations",
            help="0 = 嚴格單調；1 = 容忍 1 根反向（預設）",
        )
        sell_recovery_new = st.slider(
            "賣出回落比例", 0.3, 0.9,
            float(prefs.get("sell_recovery_pct", prefs.get("recovery_pct", sd["sell_recovery_pct"]))),
            step=0.05, key="settings_sell_recovery",
        )
        sell_kd_thresh_new = st.slider(
            "賣出 KD 閾值", 65, 95, int(prefs.get("sell_kd_d_threshold", prefs.get("kd_d_threshold", sd["sell_kd_d_threshold"]))),
            key="settings_sell_kd_thresh",
        )
        sell_lookback_new = st.slider(
            "賣出 MACD 峰谷回看根數", 10, 40,
            int(prefs.get("sell_lookback_bars", prefs.get("lookback_bars", sd["sell_lookback_bars"]))),
            key="settings_sell_lookback_bars",
        )

    if st.button("儲存 Strategy D 參數"):
        prefs.update({
            "buy_kd_window": buy_kd_window_new,
            "buy_n_bars": buy_n_bars_new,
            "buy_recovery_pct": buy_recovery_new,
            "buy_kd_k_threshold": buy_kd_thresh_new,
            "buy_max_violations": buy_max_viol_new,
            "buy_lookback_bars": buy_lookback_new,
            "sell_kd_window": sell_kd_window_new,
            "sell_n_bars": sell_n_bars_new,
            "sell_recovery_pct": sell_recovery_new,
            "sell_kd_d_threshold": sell_kd_thresh_new,
            "sell_max_violations": sell_max_viol_new,
            "sell_lookback_bars": sell_lookback_new,
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

    _render_ai_settings(user_id)
    _render_notification_settings(user_id)


def _render_ai_settings(user_id: str) -> None:
    st.markdown("---")
    st.markdown("### AI 解讀設定")
    st.caption("Dashboard 訊號解讀與新聞摘要會依序使用 Anthropic、Gemini、OpenAI；個人金鑰優先於系統 .env 金鑰。")

    providers = [
        ("Anthropic", "anthropic_api_key", "ANTHROPIC_API_KEY", "ai_anthropic_key"),
        ("Gemini", "gemini_api_key", "GEMINI_API_KEY", "ai_gemini_key"),
        ("OpenAI", "openai_api_key", "OPENAI_API_KEY", "ai_openai_key"),
    ]
    pending: dict[str, str] = {}
    clear_names: list[str] = []

    for label, secret_name, env_name, input_key in providers:
        col_status, col_input, col_clear = st.columns([1.2, 2.8, 1])
        env_set = bool(os.getenv(env_name, ""))
        user_set = has_secret(user_id, secret_name)
        if user_set:
            col_status.success(f"{label} 個人金鑰已設定")
        elif env_set:
            col_status.info(f"{label} 系統金鑰已設定")
        else:
            col_status.warning(f"{label} 未設定")
        pending[secret_name] = col_input.text_input(
            f"{label} API key（留空表示不更換）",
            type="password",
            key=input_key,
        ).strip()
        if user_set and col_clear.button("移除", key=f"clear_{secret_name}"):
            clear_names.append(secret_name)

    col_save, col_order = st.columns([1, 4])
    col_order.caption(
        f"目前 provider 順序：{os.getenv('AI_PROVIDER_ORDER', 'anthropic_haiku,gemini_flash,openai,anthropic_sonnet')}"
    )

    if col_save.button("儲存 AI 金鑰"):
        changed = False
        try:
            for secret_name, value in pending.items():
                if value:
                    set_secret(user_id, secret_name, value)
                    changed = True
            if changed:
                st.success("AI 金鑰已儲存")
                st.rerun()
            else:
                st.warning("沒有輸入新的 AI 金鑰")
        except Exception as exc:
            st.error(f"儲存失敗：{exc}")

    if clear_names:
        try:
            for secret_name in clear_names:
                clear_secret(user_id, secret_name)
            st.success("AI 個人金鑰已移除")
            st.rerun()
        except Exception as exc:
            st.error(f"移除失敗：{exc}")


def _render_watchlist_category_settings(user_id: str) -> None:
    from src.repositories.watchlist_category_repo import (
        add_item,
        create_category,
        delete_category,
        delete_item,
        list_categories,
        list_items,
    )

    st.markdown("---")
    st.markdown("### 綜合看盤分類")
    categories = list_categories(user_id)

    with st.expander("分類管理", expanded=False):
        col_name, col_add = st.columns([3, 1])
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
        items = list_items(user_id, category_id)

        if items:
            for item in items:
                col_ticker, col_name, col_delete = st.columns([1.2, 2.3, 0.8])
                col_ticker.markdown(f"**{item['ticker']}**")
                col_name.markdown(item.get("name", "") or "—")
                if col_delete.button("刪除", key=f"delete_category_item_{item['id']}"):
                    delete_item(user_id, item["id"])
                    st.rerun()
        else:
            st.caption("此分類尚無股票")

        col_ticker, col_item_name, col_note, col_add_item = st.columns([1.2, 1.8, 1.8, 0.8])
        new_item_ticker = col_ticker.text_input("代碼", key=f"new_item_ticker_{category_id}", placeholder="2330.TW")
        new_item_name = col_item_name.text_input("名稱", key=f"new_item_name_{category_id}")
        new_item_note = col_note.text_input("備註", key=f"new_item_note_{category_id}")
        if col_add_item.button("新增", key=f"add_item_{category_id}"):
            if new_item_ticker.strip():
                add_item(user_id, category_id, normalize_ticker(new_item_ticker), new_item_name, new_item_note)
                st.rerun()
            st.warning("請輸入股票代碼")

        if len(categories) > 1 and st.button("刪除此分類", key=f"delete_category_{category_id}"):
            delete_category(user_id, category_id)
            st.rerun()


def _render_notification_settings(user_id: str) -> None:
    st.markdown("---")
    st.markdown("### 通知設定")
    settings = get_settings(user_id)

    st.markdown("#### Email")
    email_enabled = st.checkbox("啟用 Email", value=bool(settings.get("email_enabled")), key="notify_email_enabled")
    col_email_to, col_smtp_host = st.columns(2)
    email_to = col_email_to.text_input("收件 Email", value=str(settings.get("email_to") or ""), key="notify_email_to")
    smtp_host = col_smtp_host.text_input("SMTP host", value=str(settings.get("smtp_host") or ""), key="notify_smtp_host")
    col_smtp_user, col_smtp_port, col_tls = st.columns([2, 1, 1])
    smtp_username = col_smtp_user.text_input("SMTP username", value=str(settings.get("smtp_username") or ""), key="notify_smtp_username")
    smtp_port = col_smtp_port.number_input("SMTP port", min_value=1, max_value=65535, value=int(settings.get("smtp_port") or 587), key="notify_smtp_port")
    smtp_use_tls = col_tls.checkbox("TLS", value=bool(settings.get("smtp_use_tls", True)), key="notify_smtp_tls")
    smtp_password = st.text_input("SMTP password / app password（留空表示不更換）", type="password", key="notify_smtp_password")

    st.markdown("#### Telegram")
    telegram_enabled = st.checkbox("啟用 Telegram", value=bool(settings.get("telegram_enabled")), key="notify_telegram_enabled")
    col_chat, col_token = st.columns(2)
    telegram_chat_id = col_chat.text_input("Telegram chat_id", value=str(settings.get("telegram_chat_id") or ""), key="notify_telegram_chat")
    telegram_token = col_token.text_input("Telegram bot token（留空表示不更換）", type="password", key="notify_telegram_token")

    st.markdown("#### 通道對映")
    channel_options = ["inbox", "email", "telegram"]
    price_channels = st.multiselect(
        "價格警示通道",
        channel_options,
        default=[c for c in settings.get("price_alert_channels", ["inbox"]) if c in channel_options],
        key="notify_price_channels",
    )
    strategy_channels = st.multiselect(
        "策略掃描通道",
        channel_options,
        default=[c for c in settings.get("strategy_alert_channels", ["inbox"]) if c in channel_options],
        key="notify_strategy_channels",
    )
    weekly_channels = st.multiselect(
        "週報通道",
        channel_options,
        default=[c for c in settings.get("weekly_digest_channels", ["inbox"]) if c in channel_options],
        key="notify_weekly_channels",
    )

    col_save, col_test = st.columns(2)
    if col_save.button("儲存通知設定"):
        save_settings(user_id, {
            "email_enabled": email_enabled,
            "email_to": email_to.strip(),
            "smtp_host": smtp_host.strip(),
            "smtp_port": int(smtp_port),
            "smtp_username": smtp_username.strip(),
            "smtp_use_tls": bool(smtp_use_tls),
            "telegram_enabled": telegram_enabled,
            "telegram_chat_id": telegram_chat_id.strip(),
            "inbox_enabled": True,
            "price_alert_channels": price_channels or ["inbox"],
            "strategy_alert_channels": strategy_channels or ["inbox"],
            "weekly_digest_channels": weekly_channels or ["inbox"],
        })
        if smtp_password.strip():
            set_secret(user_id, "smtp_password", smtp_password.strip())
        if telegram_token.strip():
            set_secret(user_id, "telegram_bot_token", telegram_token.strip())
        st.success("通知設定已儲存")
        st.rerun()

    if col_test.button("傳送測試通知"):
        results = send_notification(
            user_id,
            "Stock Intelligence 測試通知",
            "這是一則測試訊息。若外部通道失敗，Inbox 仍會保留此訊息。",
            severity="info",
            event_type="price_alert",
        )
        st.write([result.__dict__ for result in results])
