import streamlit as st

from src.backtest.engine import run_backtest
from src.backtest.metrics import compute_metrics
from src.backtest.visualizer import build_equity_curve, build_return_distribution
from src.data.ticker_utils import normalize_ticker


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 回測分析 — Strategy D")
    st.caption("以過去 1 年歷史資料計算所有訊號的前瞻報酬")

    col1, col2, col3 = st.columns([2, 1, 1])
    ticker = col1.text_input("股票代號", value=cfg.get("ticker", "2330.TW")).strip().upper()
    forward_days = col2.selectbox("前瞻天數", [20, 40, 60, 120], index=2)
    run_btn = col3.button("執行回測", use_container_width=True)

    if not run_btn:
        st.info("設定參數後點擊「執行回測」")
        return

    ticker = normalize_ticker(ticker)
    with st.spinner(f"回測 {ticker} 中…"):
        bt_df = run_backtest(ticker, cfg["strategy_d"], forward_days=forward_days, years=1)

    if bt_df.empty:
        st.warning(f"**{ticker}** 在過去 1 年內未找到 Strategy D 訊號，無法回測。")
        return

    metrics = compute_metrics(bt_df, forward_days=forward_days)

    # ── Metrics cards ──
    st.markdown("### 績效摘要")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("訊號次數", metrics["count"])
    c2.metric("勝率", f"{metrics['win_rate']:.1f}%")
    c3.metric("總報酬", f"{metrics['total_return_pct']:+.1f}%")
    c4.metric("平均報酬", f"{metrics['mean_return_pct']:+.1f}%")
    c5.metric("MDD", f"{metrics['max_drawdown_pct']:.1f}%")
    c6.metric("Sharpe", f"{metrics['sharpe']:.2f}")

    st.markdown("---")

    # ── Charts ──
    st.plotly_chart(build_equity_curve(bt_df), use_container_width=True,
                    config={"displayModeBar": False})
    st.plotly_chart(build_return_distribution(bt_df), use_container_width=True,
                    config={"displayModeBar": False})

    # ── Raw data table ──
    with st.expander("訊號明細"):
        display_df = bt_df[["date", "signal_close", "forward_date", "forward_close",
                             "forward_return_pct", "win"]].copy()
        display_df.columns = ["訊號日", "進場價", "前瞻日", "前瞻收盤", "報酬 (%)", "獲利"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
