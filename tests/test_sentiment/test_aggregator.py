from src.sentiment.aggregator import aggregate_sentiment, alignment_bucket


def test_alignment_bucket_classifies_sources():
    assert alignment_bucket([0.4, 0.2, 0.3]) == "Bullish"
    assert alignment_bucket([-0.4, -0.2]) == "Bearish"
    assert alignment_bucket([0.1, 0.0, -0.1]) == "Tight"
    assert alignment_bucket([0.8, -0.4]) == "Wide divergence"
    assert alignment_bucket([0.6, -0.2, 0.1]) == "Mixed"


def test_aggregate_sentiment_combines_news_and_external_sources(monkeypatch):
    import src.sentiment.aggregator as module

    monkeypatch.setattr(module, "get_market_cache", lambda key, ttl_override=None: None)
    saved = {}
    monkeypatch.setattr(module, "save_market_cache", lambda key, value: saved.update({key: value}))

    result = aggregate_sentiment(
        "TSLA",
        [{"headline": "Tesla strong growth", "summary": "bullish demand"}],
        fetchers={
            "reddit": lambda ticker: {"source": "reddit", "title": "Reddit", "score": 0.2, "label": "positive", "count": 3, "status": "ok"},
            "stocktwits": lambda ticker: {"source": "stocktwits", "title": "Stocktwits", "score": -0.1, "label": "negative", "count": 2, "status": "ok"},
            "ptt": lambda ticker: {"source": "ptt", "title": "PTT", "score": 0.0, "label": "neutral", "count": 1, "status": "ok"},
        },
    )

    assert result["ticker"] == "TSLA"
    assert result["source_count"] == 4
    assert len(result["sources"]) == 4
    assert saved


def test_aggregate_sentiment_marks_failed_source_unavailable(monkeypatch):
    import src.sentiment.aggregator as module

    monkeypatch.setattr(module, "get_market_cache", lambda key, ttl_override=None: None)
    monkeypatch.setattr(module, "save_market_cache", lambda key, value: None)

    result = aggregate_sentiment(
        "TSLA",
        [],
        fetchers={"reddit": lambda ticker: (_ for _ in ()).throw(RuntimeError("blocked"))},
    )

    reddit = next(source for source in result["sources"] if source["source"] == "reddit")
    assert reddit["status"] == "unavailable"
    assert reddit["message"] == "Reddit 暫不可用"
