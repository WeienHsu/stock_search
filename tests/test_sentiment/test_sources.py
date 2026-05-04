from src.sentiment.sources import ptt, reddit, stocktwits
from src.sentiment.sources.ptt_synonyms import query_terms_for_ticker


def test_stocktwits_uses_bearer_token_when_configured(monkeypatch):
    captured = {}

    def fake_fetch_json(url, *, timeout=5, headers=None):
        captured["headers"] = headers
        return {"messages": [{"body": "strong growth"}]}

    monkeypatch.setenv("STOCKTWITS_ACCESS_TOKEN", "token-123")
    monkeypatch.setattr(stocktwits, "fetch_json", fake_fetch_json)

    result = stocktwits.fetch_stocktwits_sentiment("TSLA")

    assert captured["headers"] == {"Authorization": "Bearer token-123"}
    assert result["source"] == "stocktwits"
    assert result["count"] == 1


def test_stocktwits_works_without_token(monkeypatch):
    captured = {}

    def fake_fetch_json(url, *, timeout=5, headers=None):
        captured["headers"] = headers
        return {"messages": []}

    monkeypatch.delenv("STOCKTWITS_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(stocktwits, "fetch_json", fake_fetch_json)

    result = stocktwits.fetch_stocktwits_sentiment("TSLA")

    assert captured["headers"] is None
    assert result["status"] == "empty"


def test_ptt_uses_taiwan_stock_synonyms(monkeypatch):
    requested_terms = []

    def fake_fetch_text(url, *, timeout=5):
        requested_terms.append(url)
        return '<div class="title"><a>台積電 strong outlook</a></div>'

    monkeypatch.setattr(ptt, "fetch_text", fake_fetch_text)

    result = ptt.fetch_ptt_sentiment("2330.TW")

    assert "2330" in query_terms_for_ticker("2330.TW")
    assert "台積電" in query_terms_for_ticker("2330.TW")
    assert any("%E5%8F%B0%E7%A9%8D%E9%9B%BB" in url for url in requested_terms)
    assert result["count"] == 1


def test_reddit_falls_back_to_web_json_without_oauth(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("REDDIT_REFRESH_TOKEN", raising=False)
    monkeypatch.setattr(
        reddit,
        "fetch_json",
        lambda url, *, timeout=5: {
            "data": {
                "children": [
                    {"data": {"title": "TSLA demand strong", "selftext": "bullish delivery"}},
                ]
            }
        },
    )

    result = reddit.fetch_reddit_sentiment("TSLA")

    assert result["source"] == "reddit"
    assert result["count"] == 1
