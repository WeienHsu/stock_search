import streamlit as st

from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker
from src.repositories.risk_settings_repo import get_risk_settings, save_risk_settings
from src.risk.atr_stoploss import compute_atr_stoploss
from src.risk.position_sizer import compute_position_size


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 風險控管")

    risk = get_risk_settings(user_id)

    # ── Settings ──
    st.markdown("### 風險參數")
    col1, col2, col3 = st.columns(3)
    portfolio = col1.number_input("投資組合規模 (TWD / USD)", value=int(risk["portfolio_size"]),
                                  step=10000, min_value=1000)
    max_risk  = col2.number_input("單筆最大風險 (%)", value=float(risk["max_risk_per_trade_pct"]),
                                  step=0.1, min_value=0.1, max_value=5.0)
    atr_mult  = col3.number_input("ATR 停損倍數", value=float(risk["atr_multiplier"]),
                                  step=0.5, min_value=0.5, max_value=5.0)

    if st.button("儲存風險設定"):
        save_risk_settings(user_id, {
            "portfolio_size": portfolio,
            "max_risk_per_trade_pct": max_risk,
            "atr_multiplier": atr_mult,
        })
        st.success("已儲存")

    st.divider()
    st.markdown("### 部位計算")

    ticker = st.text_input("股票代號", value=cfg.get("ticker", "2330.TW")).strip().upper()
    calc_btn = st.button("計算建議部位")

    if not calc_btn:
        st.info("輸入股票代號後點擊「計算建議部位」")
        return

    ticker = normalize_ticker(ticker)
    with st.spinner(f"載入 {ticker} 資料…"):
        df = fetch_prices_for_strategy(ticker, years=1)

    if df.empty:
        st.error("無法取得資料")
        return

    entry_price = float(df["close"].iloc[-1])

    try:
        sl = compute_atr_stoploss(df, entry_price=entry_price,
                                  atr_multiplier=atr_mult)
        pos = compute_position_size(
            portfolio_size=portfolio,
            max_risk_pct=max_risk,
            risk_per_share=sl["risk_per_share"],
            entry_price=entry_price,
        )
    except Exception as e:
        st.error(f"計算失敗：{e}")
        return

    # ── Results ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價（進場參考）", f"{entry_price:.2f}")
    c2.metric("ATR 停損價", f"{sl['stop_price']:.2f}")
    c3.metric("每股風險", f"{sl['risk_per_share']:.2f}")
    c4.metric("ATR 值", f"{sl['atr_value']:.4f}")

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("建議股數", f"{pos['shares']:,}")
    c2.metric("部位市值", f"{pos['position_value']:,.0f}")
    c3.metric("實際風險金額", f"{pos['actual_risk_amount']:,.0f}")
    c4.metric("部位佔組合", f"{pos['position_pct']:.1f}%")

    st.caption(f"計算基礎：ATR{14}×{atr_mult} 停損，單筆最大風險 {max_risk}% × 組合 {portfolio:,}")
