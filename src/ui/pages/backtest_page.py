import streamlit as st

from src.backtest.engine import run_backtest
from src.backtest.metrics import compute_metrics
from src.backtest.visualizer import build_equity_curve, build_return_distribution
from src.core.strategy_registry import list_strategies
from src.data.ticker_utils import normalize_ticker

import src.strategies.strategy_d   # ensure registration
import src.strategies.strategy_kd  # ensure registration

_STRATEGY_LABELS = {
    "strategy_d":  "Strategy D（MACD + KD）",
    "strategy_kd": "Strategy KD（黃金 / 死亡交叉）",
}


def render(cfg: dict, user_id: str) -> None:
    st.markdown("## 回測分析")
    st.caption("以過去 1 年歷史資料計算所有訊號的前瞻報酬")

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    ticker = col1.text_input("股票代號", value=cfg.get("ticker", "2330.TW")).strip().upper()

    available = list_strategies()
    strategy_id = col2.selectbox(
        "策略",
        options=available,
        index=0,
        format_func=lambda x: _STRATEGY_LABELS.get(x, x),
        key="bt_strategy",
    )

    with col3:
        forward_days = st.slider(
            "前瞻天數（交易日）",
            min_value=5, max_value=500, value=60, step=5,
            help=(
                "訊號觸發後，持倉第 N 個**交易日**的報酬。\n\n"
                "• 5–20 日：短線（1–4 週）\n"
                "• 20–60 日：中線（1–3 個月）\n"
                "• 60–250 日：波段（3–12 個月）\n"
                "• 250+ 日：長線（1 年以上，~250 交易日 ≈ 1 年）"
            ),
        )

    signal_type = col4.radio(
        "訊號類型",
        options=["buy", "sell"],
        format_func=lambda x: "📈 買進" if x == "buy" else "📉 賣出",
        key="bt_signal_type",
    )
    run_btn = st.button("執行回測", use_container_width=False)

    if not run_btn:
        st.info("設定參數後點擊「執行回測」")
        return

    ticker = normalize_ticker(ticker)
    label = "買進" if signal_type == "buy" else "賣出"
    strategy_params = cfg.get(strategy_id, {})

    with st.spinner(f"回測 {ticker} {_STRATEGY_LABELS.get(strategy_id, strategy_id)} {label}訊號中…"):
        bt_df = run_backtest(
            ticker,
            strategy_id=strategy_id,
            strategy_params=strategy_params,
            forward_days=forward_days,
            years=1,
            signal_type=signal_type,
        )

    strategy_label = _STRATEGY_LABELS.get(strategy_id, strategy_id)
    if bt_df.empty:
        st.warning(f"**{ticker}** 在過去 1 年內未找到 {strategy_label} {label}訊號，無法回測。")
        return

    metrics = compute_metrics(bt_df, forward_days=forward_days)

    # ── Metrics cards ──
    st.markdown(f"### 績效摘要（{strategy_label} — {label}訊號）")
    win_label = "勝率" if signal_type == "buy" else "空頭勝率"
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("訊號次數", metrics["count"])
    c2.metric(win_label, f"{metrics['win_rate']:.1f}%")
    c3.metric("累積報酬", f"{metrics['total_return_pct']:+.1f}%")
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
