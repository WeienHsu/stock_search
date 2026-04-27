def analyze_sentiment(articles: list[dict]) -> dict:
    if not articles:
        return {"score": 0.0, "label": "neutral", "article_count": 0}

    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
    except LookupError:
        import nltk
        nltk.download("vader_lexicon", quiet=True)
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
    except Exception:
        return {"score": 0.0, "label": "neutral", "article_count": len(articles)}

    scores = []
    for art in articles:
        text = (art.get("headline", "") + " " + art.get("summary", "")).strip()
        if text:
            scores.append(sia.polarity_scores(text)["compound"])

    if not scores:
        return {"score": 0.0, "label": "neutral", "article_count": len(articles)}

    avg = sum(scores) / len(scores)
    label = "positive" if avg > 0.05 else "negative" if avg < -0.05 else "neutral"

    return {"score": round(avg, 4), "label": label, "article_count": len(articles)}
