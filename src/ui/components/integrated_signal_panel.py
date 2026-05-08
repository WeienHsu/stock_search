from __future__ import annotations

import pandas as pd
import streamlit as st


def _strategy_d_summary(
    signal_layers: list,
    vp_ctx: dict | None,
    today_str: str,
) -> None:
    """Render Strategy D conclusions block (left column)."""
    from src.ui.charts.kline_chart import SignalLayer

    d_layers = [l for l in signal_layers if getattr(l, "strategy_id", "") == "strategy_d"]
    if not d_layers:
        st.caption("Strategy D 未啟用")
        return

    layer = d_layers[0]
    buy_dates = sorted(layer.buy_dates)
    sell_dates = sorted(layer.sell_dates)

    last_buy = buy_dates[-1][:10] if buy_dates else None
    last_sell = sell_dates[-1][:10] if sell_dates else None
    today_buy = any(d[:10] == today_str for d in buy_dates)
    today_sell = any(d[:10] == today_str for d in sell_dates)

    if today_buy:
        st.html('<span class="signal-buy" role="status" aria-label="今日有買進訊號">▲ 今日有買進訊號</span>')
    elif last_buy:
        days_since = (pd.Timestamp(today_str) - pd.Timestamp(last_buy)).days
        st.info(f"最近買進：{last_buy}（{days_since} 天前）")
    else:
        st.info("無近期買進訊號")

    if today_sell:
        st.html('<span class="signal-sell" role="status" aria-label="今日有賣出訊號">▼ 今日有賣出訊號</span>')
    elif last_sell:
        days_since = (pd.Timestamp(today_str) - pd.Timestamp(last_sell)).days
        st.info(f"最近賣出：{last_sell}（{days_since} 天前）")

    if vp_ctx:
        poc_dist = vp_ctx.get("poc_distance_pct")
        in_zone = vp_ctx.get("in_support_zone", False)
        if poc_dist is not None:
            sign = "+" if float(poc_dist) >= 0 else ""
            st.caption(f"距 POC：**{sign}{float(poc_dist):.2f}%**　{'✓ 支撐帶內' if in_zone else '—'}")


def _ma_analysis_summary(summary: dict) -> None:
    """Render MA analysis conclusions block (right column)."""
    arrow_map = {"上行": "↑", "下彎": "↓", "持平": "→"}
    st.markdown(f"**多頭排列：** {summary.get('stars', '—')} ({summary.get('score', 0)}/4)")
    st.markdown(f"**月線 > 季線：** {'是 ✅' if summary.get('month_above_quarter') else '否 ❌'}")

    directions = summary.get("directions", {})
    if directions:
        parts = []
        for period in [5, 20, 60, 120]:
            d = directions.get(period, "持平")
            parts.append(f"MA{period} {arrow_map.get(d, '→')}")
        st.caption("  |  ".join(parts))

    recent_crosses = summary.get("recent_crosses", [])
    if recent_crosses:
        last = recent_crosses[-1]
        ctype = last.get("type", "")
        label = "黃金交叉 ✅" if "golden" in ctype else "死亡交叉 ❌"
        cross_date = str(last.get("date", ""))[:10]
        st.caption(f"近期交叉：{label} @ {cross_date}")


def _combined_verdict(summary: dict, signal_layers: list, vp_ctx: dict | None, today_str: str) -> str:
    """Return a one-line combined verdict string."""
    from src.ui.charts.kline_chart import SignalLayer

    ma_score: int = summary.get("score", 0)
    month_above: bool = summary.get("month_above_quarter", False)

    d_layers = [l for l in signal_layers if getattr(l, "strategy_id", "") == "strategy_d"]
    buy_dates = sorted(d_layers[0].buy_dates) if d_layers else []
    last_buy = buy_dates[-1][:10] if buy_dates else None
    today_buy = any(d[:10] == today_str for d in buy_dates)
    recent_buy = last_buy and (pd.Timestamp(today_str) - pd.Timestamp(last_buy)).days <= 3

    in_zone = vp_ctx.get("in_support_zone", False) if vp_ctx else False

    if ma_score >= 3 and month_above and (today_buy or recent_buy) and in_zone:
        return "⭐ 強烈進場條件：MA 多頭排列 + Strategy D 近期買訊 + 位於支撐帶"
    if ma_score >= 3 and month_above and (today_buy or recent_buy):
        return "✅ 進場條件良好：MA 多頭 + Strategy D 近期買訊"
    if ma_score >= 3 and month_above:
        return "📈 趨勢偏多，但尚無 Strategy D 買進訊號，可持續觀察"
    if today_buy or recent_buy:
        return "⚠️ Strategy D 近期買訊，但均線趨勢偏弱，宜謹慎"
    if ma_score <= 1:
        return "📉 均線空頭排列，趨勢不佳"
    return "📊 目前無明確方向訊號"


def render_integrated_signal(
    df_full: pd.DataFrame,
    ma_summary: dict,
    signal_layers: list,
    vp_ctx: dict | None = None,
    *,
    use_expander: bool = True,
) -> None:
    """Render two-column integrated view: Strategy D (left) + MA analysis (right) + verdict."""
    today_str = str(df_full["date"].iloc[-1])[:10] if not df_full.empty else ""

    def _render_content() -> None:
        col_d, col_ma = st.columns(2)

        with col_d:
            st.markdown("#### Strategy D")
            _strategy_d_summary(signal_layers, vp_ctx, today_str)

        with col_ma:
            st.markdown("#### 均線分析")
            _ma_analysis_summary(ma_summary)

        verdict = _combined_verdict(ma_summary, signal_layers, vp_ctx, today_str)
        st.info(verdict)

    if use_expander:
        st.divider()
        with st.expander("📊 整合訊號判讀", expanded=True):
            _render_content()
    else:
        _render_content()
