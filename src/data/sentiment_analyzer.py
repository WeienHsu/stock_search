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
