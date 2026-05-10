from __future__ import annotations

import streamlit as st

_LABEL_COLORS = {
    "positive": "#6A9E8A",
    "negative": "#C87D6A",
    "neutral": "#8A8480",
}
_ALIGNMENT_TEXT = {
    "Bullish": "多方一致",
    "Bearish": "空方一致",
    "Tight": "來源一致",
    "Mixed": "分歧",
    "Wide divergence": "高度分歧",
    "Unavailable": "資料不足",
}


_PREDICTION_MARKET_SOURCES = {"polymarket"}


def render_sentiment_panel(aggregate: dict) -> None:
    st.markdown("### 情緒儀表板")
    score = float(aggregate.get("score", 0.0) or 0.0)
    alignment = str(aggregate.get("alignment") or "Unavailable")
    st.metric(
        "跨來源平均情緒",
        f"{score:+.2f}",
        _ALIGNMENT_TEXT.get(alignment, alignment),
    )

    sources = aggregate.get("sources") or []
    if not sources:
        st.caption("尚無可用情緒來源")
        return

    news_sources = [s for s in sources if s.get("source") not in _PREDICTION_MARKET_SOURCES]
    market_sources = [s for s in sources if s.get("source") in _PREDICTION_MARKET_SOURCES]

    for source in news_sources:
        _render_source_row(source)

    if market_sources:
        st.caption("預測市場（反映總體市場情緒，非個股）")
        for source in market_sources:
            _render_source_row(source)


def _render_source_row(source: dict) -> None:
    title = str(source.get("title") or source.get("source") or "Source")
    score = float(source.get("score", 0.0) or 0.0)
    label = str(source.get("label") or "neutral")
    status = str(source.get("status") or "")
    count = int(source.get("count") or 0)
    color = _LABEL_COLORS.get(label, "#8A8480")
    progress = max(0.0, min(1.0, (score + 1.0) / 2.0))

    cols = st.columns([1.2, 3, 0.9])
    cols[0].markdown(f"**{title}**")
    cols[1].progress(progress, text=f"{label} {score:+.2f}")
    if status == "ok":
        cols[2].html(f'<span role="status" style="color:{color}; font-weight:600">{count} 筆</span>')
    else:
        message = str(source.get("message") or status or "暫不可用")
        cols[2].caption(message)
