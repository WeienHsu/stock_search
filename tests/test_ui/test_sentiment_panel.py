from src.sentiment.score_glossary import SCORE_GLOSSARY_MARKDOWN, SCORE_HELP
from src.ui.components import sentiment_panel


class _Expander:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_score_help_documents_existing_sentiment_thresholds():
    assert "-1.0 到 +1.0" in SCORE_HELP
    assert "+0.05" in SCORE_HELP
    assert "-0.05" in SCORE_HELP


def test_score_glossary_documents_alignment_and_polymarket_rules():
    assert "多方一致" in SCORE_GLOSSARY_MARKDOWN
    assert "所有可用來源分數都大於 `+0.05`" in SCORE_GLOSSARY_MARKDOWN
    assert "來源分數極差小於等於 `0.30`" in SCORE_GLOSSARY_MARKDOWN
    assert "Polymarket" in SCORE_GLOSSARY_MARKDOWN
    assert "成交量加權" in SCORE_GLOSSARY_MARKDOWN


def test_sentiment_panel_adds_metric_help_and_collapsed_glossary(monkeypatch):
    captured = {"markdown": [], "metric": None, "expander": None, "caption": []}

    monkeypatch.setattr(sentiment_panel.st, "markdown", lambda text: captured["markdown"].append(text))
    monkeypatch.setattr(sentiment_panel.st, "caption", lambda text: captured["caption"].append(text))

    def fake_metric(label, value, delta, help=None):
        captured["metric"] = {
            "label": label,
            "value": value,
            "delta": delta,
            "help": help,
        }

    def fake_expander(label, expanded=False):
        captured["expander"] = {"label": label, "expanded": expanded}
        return _Expander()

    monkeypatch.setattr(sentiment_panel.st, "metric", fake_metric)
    monkeypatch.setattr(sentiment_panel.st, "expander", fake_expander)

    sentiment_panel.render_sentiment_panel({
        "score": 0.11,
        "alignment": "Bullish",
        "sources": [],
    })

    assert captured["metric"] == {
        "label": "跨來源平均情緒",
        "value": "+0.11",
        "delta": "多方一致",
        "help": SCORE_HELP,
    }
    assert captured["expander"] == {"label": "ⓘ 如何解讀情緒分數？", "expanded": False}
    assert SCORE_GLOSSARY_MARKDOWN in captured["markdown"]
    assert "尚無可用情緒來源" in captured["caption"]
