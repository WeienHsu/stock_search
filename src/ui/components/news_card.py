from datetime import datetime

import streamlit as st

from config.morandi_palette import GREEN, RED


def render_news_section(articles: list[dict], sentiment: dict) -> None:
    score = sentiment.get("score", 0.0)
    label = sentiment.get("label", "neutral")
    count = sentiment.get("article_count", 0)

    if label == "positive":
        color, icon = GREEN, "↑"
    elif label == "negative":
        color, icon = RED, "↓"
    else:
        color, icon = "#8A8480", "—"

    st.markdown(
        f"**市場情緒** &nbsp;&nbsp;"
        f'<span style="color:{color}; font-weight:600">{icon} {label.upper()} ({score:+.2f})</span>'
        f'&nbsp; <span style="color:#8A8480; font-size:0.85em">{count} 篇新聞</span>',
        unsafe_allow_html=True,
    )

    if not articles:
        st.caption("無最新新聞")
        return

    for art in articles[:5]:
        ts = art.get("datetime", 0)
        date_str = datetime.fromtimestamp(ts).strftime("%m/%d") if ts else ""
        headline = art.get("headline", "")
        url = art.get("url", "")
        source = art.get("source", "")
        if url:
            st.markdown(
                f'<div style="font-size:0.88em; margin:4px 0">'
                f'<span style="color:#8A8480">{date_str} {source}</span><br>'
                f'<a href="{url}" target="_blank" style="color:#4A4540">{headline}</a>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size:0.88em; margin:4px 0">'
                f'<span style="color:#8A8480">{date_str} {source}</span><br>'
                f'{headline}'
                f'</div>',
                unsafe_allow_html=True,
            )
