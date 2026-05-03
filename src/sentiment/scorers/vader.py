from __future__ import annotations

from typing import Any

_POSITIVE_TERMS = {
    "beat", "bull", "bullish", "buy", "gain", "growth", "higher", "profit", "rally", "strong", "up",
    "利多", "上漲", "成長", "獲利", "看多", "強勢", "買進",
}
_NEGATIVE_TERMS = {
    "bear", "bearish", "cut", "decline", "down", "fall", "loss", "miss", "risk", "sell", "weak",
    "利空", "下跌", "虧損", "風險", "看空", "弱勢", "賣出",
}


def score_texts(texts: list[str]) -> dict[str, Any]:
    clean_texts = [text.strip() for text in texts if text and text.strip()]
    if not clean_texts:
        return {"score": 0.0, "label": "neutral", "article_count": 0}

    scores = [_score_text(text) for text in clean_texts]
    avg = sum(scores) / len(scores)
    return {
        "score": round(avg, 4),
        "label": label_for_score(avg),
        "article_count": len(clean_texts),
    }


def label_for_score(score: float) -> str:
    if score > 0.05:
        return "positive"
    if score < -0.05:
        return "negative"
    return "neutral"


def _score_text(text: str) -> float:
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer

        return float(SentimentIntensityAnalyzer().polarity_scores(text)["compound"])
    except LookupError:
        try:
            import nltk

            nltk.download("vader_lexicon", quiet=True)
            from nltk.sentiment.vader import SentimentIntensityAnalyzer

            return float(SentimentIntensityAnalyzer().polarity_scores(text)["compound"])
        except Exception:
            return _lexicon_score(text)
    except Exception:
        return _lexicon_score(text)


def _lexicon_score(text: str) -> float:
    lower = text.lower()
    positives = sum(1 for term in _POSITIVE_TERMS if term in lower)
    negatives = sum(1 for term in _NEGATIVE_TERMS if term in lower)
    total = positives + negatives
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (positives - negatives) / total))
