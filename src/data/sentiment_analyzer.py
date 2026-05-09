import streamlit as st

from src.data.dynamic_ttl import get_ttl


@st.cache_data(ttl=get_ttl(300), show_spinner=False)
def analyze_sentiment(articles: list[dict]) -> dict:
    from src.sentiment.scorers.vader import score_texts

    texts = [
        f"{article.get('headline', '')} {article.get('summary', '')}".strip()
        for article in articles
    ]
    scored = score_texts(texts)
    return {
        "score": scored["score"],
        "label": scored["label"],
        "article_count": len(articles),
    }
