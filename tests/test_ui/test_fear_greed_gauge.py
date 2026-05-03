from src.ui.components.fear_greed_gauge import build_fear_greed_gauge


def test_build_fear_greed_gauge_has_no_invalid_indicator_properties():
    fig = build_fear_greed_gauge({"score": 66.6, "rating": "greed"})

    assert len(fig.data) == 2
    assert fig.layout.showlegend is False
