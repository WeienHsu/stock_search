from datetime import datetime
from html import escape

import streamlit as st

from src.ai.prompts.news_synthesizer import generate_news_summary
from src.ai.provider_chain import build_default_chain
from src.ai.providers.base import AIProviderError, MissingAIProviderConfig
from config.morandi_palette import GREEN, RED


def render_news_section(
    articles: list[dict],
    sentiment: dict,
    ticker: str | None = None,
    user_id: str | None = None,
) -> None:
    score = sentiment.get("score", 0.0)
    label = sentiment.get("label", "neutral")
    count = sentiment.get("article_count", 0)

    if label == "positive":
        color, icon = GREEN, "↑"
    elif label == "negative":
        color, icon = RED, "↓"
    else:
        color, icon = "#8A8480", "—"

    st.html(
        f"**市場情緒** &nbsp;&nbsp;"
        f'<span style="color:{color}; font-weight:600">{icon} {label.upper()} ({score:+.2f})</span>'
        f'&nbsp; <span style="color:#8A8480; font-size:0.85em">{count} 篇新聞</span>'
    )

    if not articles:
        st.caption("無最新新聞")
        return

    if ticker and user_id:
        _render_ai_news_summary(ticker, user_id, articles, sentiment)

    for art in articles[:5]:
        ts = art.get("datetime", 0)
        date_str = datetime.fromtimestamp(ts).strftime("%m/%d") if ts else ""
        headline = escape(str(art.get("headline", "")))
        url = escape(str(art.get("url", "")), quote=True)
        source = escape(str(art.get("source", "")))
        if url:
            st.html(
                f'<div style="font-size:0.88em; margin:4px 0">'
                f'<span style="color:#8A8480">{date_str} {source}</span><br>'
                f'<a href="{url}" target="_blank" style="color:#4A4540">{headline}</a>'
                f'</div>'
            )
        else:
            st.html(
                f'<div style="font-size:0.88em; margin:4px 0">'
                f'<span style="color:#8A8480">{date_str} {source}</span><br>'
                f'{headline}'
                f'</div>'
            )


def _render_ai_news_summary(ticker: str, user_id: str, articles: list[dict], sentiment: dict) -> None:
    key = f"ai_news_summary_{ticker}"
    if st.button("🤖 新聞摘要", key=f"btn_ai_news_{ticker}", help="用已設定的 AI provider 摘要近期新聞"):
        with st.spinner("產生新聞摘要…"):
            try:
                chain = build_default_chain(user_id)
                st.session_state[key] = generate_news_summary(chain, ticker, articles, sentiment)
            except MissingAIProviderConfig:
                st.session_state[key] = ""
                st.info("尚未設定 AI API key，可至設定頁新增 Anthropic、Gemini 或 OpenAI key。")
            except AIProviderError as exc:
                st.session_state[key] = ""
                st.error(f"AI 新聞摘要失敗：{exc}")
            except Exception as exc:
                st.session_state[key] = ""
                st.error(f"AI 新聞摘要失敗：{exc}")

    if st.session_state.get(key):
        with st.expander("AI 新聞摘要", expanded=True):
            st.markdown(st.session_state[key])
