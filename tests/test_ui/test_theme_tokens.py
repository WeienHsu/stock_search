import pandas as pd

from scripts.check_contrast import contrast_ratio
from src.backtest.visualizer import build_equity_curve, build_return_distribution
from src.ui.components.index_mini_chart import build_bar_chart, build_index_sparkline
from src.ui.theme import styles
from src.ui.theme.plotly_template import get_chart_palette, get_plotly_template
from src.ui.theme.tokens import (
    MOTION_TOKEN_KEYS,
    SPACING_TOKEN_KEYS,
    TOKEN_REGISTRY_KEYS,
    TYPOGRAPHY_TOKEN_KEYS,
    get_token_registry,
    get_tokens,
)
from src.ui.utils.styler import apply_up_down_style


def test_token_registry_groups_all_foundation_categories():
    assert set(TOKEN_REGISTRY_KEYS) == {"colors", "spacing", "typography", "motion"}

    for theme in ("morandi", "dark"):
        registry = get_token_registry(theme)
        tokens = get_tokens(theme)

        assert set(registry["spacing"]) == set(SPACING_TOKEN_KEYS)
        assert set(registry["typography"]) == set(TYPOGRAPHY_TOKEN_KEYS)
        assert set(registry["motion"]) == set(MOTION_TOKEN_KEYS)
        assert registry["colors"]["chart_up"] == tokens["semantic_up"]
        assert registry["colors"]["chart_down"] == tokens["semantic_down"]
        assert registry["colors"]["chart_grid"] == tokens["border_default"]


def test_metric_delta_css_uses_tw_market_up_down_tokens(monkeypatch):
    captured = {}

    monkeypatch.setattr(styles.st, "html", lambda html: captured.setdefault("html", html))

    styles.inject_css("morandi")

    html = captured["html"]
    assert "stMetricDeltaIcon-Up" in html
    assert "stMetricDeltaIcon-Down" in html
    assert "--space-md:" in html
    assert "--motion-fast:" in html


def test_sidebar_and_secondary_button_contrast_tokens_are_readable():
    for theme in ("morandi", "dark"):
        tokens = get_tokens(theme)

        assert contrast_ratio(tokens["text_primary"], tokens["sidebar_bg"]) >= 4.5
        assert contrast_ratio(tokens["sidebar_text_secondary"], tokens["sidebar_bg"]) >= 4.5
        assert contrast_ratio(tokens["text_primary"], tokens["sidebar_nav_active_bg"]) >= 4.5
        assert contrast_ratio(tokens["text_primary"], tokens["control_bg"]) >= 4.5
        assert contrast_ratio(tokens["text_primary"], tokens["button_secondary_bg"]) >= 4.5
        assert contrast_ratio(tokens["text_primary"], tokens["button_secondary_hover_bg"]) >= 4.5


def test_dark_mode_sidebar_and_button_css_targets_streamlit_controls(monkeypatch):
    captured = {}

    monkeypatch.setattr(styles.st, "html", lambda html: captured.setdefault("html", html))

    styles.inject_css("dark")

    html = captured["html"]
    assert "--sidebar-bg:" in html
    assert "--sidebar-text-secondary:" in html
    assert '[data-testid="stSidebar"] [data-testid="stSidebarNav"] a' in html
    assert '[data-testid="stSidebar"] input' in html
    assert '[data-testid="stSidebar"] [data-testid="stSegmentedControl"] button' in html
    assert '[data-testid="baseButton-secondary"]' in html
    assert '[data-testid="stBaseButton-secondary"]' in html
    assert "button-secondary-hover-bg" in html


def test_up_down_styler_uses_shared_tw_market_colors(monkeypatch):
    import src.ui.utils.styler as styler_module

    monkeypatch.setattr(styler_module, "get_current_theme", lambda: "morandi")

    html = apply_up_down_style(pd.DataFrame({"change": [1.0, -1.0, 0.0]}), ["change"]).to_html()
    tokens = get_tokens("morandi")

    assert tokens["semantic_up_text"] in html
    assert tokens["semantic_down_text"] in html
    assert tokens["text_secondary"] in html


def test_plotly_template_and_palette_are_token_backed():
    tokens = get_tokens("morandi")
    palette = get_chart_palette("morandi")
    template = get_plotly_template("morandi")

    assert palette.MORANDI_UP == tokens["chart_up"]
    assert palette.MORANDI_DOWN == tokens["chart_down"]
    assert palette.MA_COLORS[60] == tokens["chart_ma_60"]
    assert template["layout"]["xaxis"]["gridcolor"] == tokens["chart_grid"]
    assert template["layout"]["yaxis"]["gridcolor"] == tokens["chart_grid"]


def test_small_plotly_components_use_shared_palette(monkeypatch):
    import src.ui.theme.plotly_template as plotly_module

    monkeypatch.setattr(plotly_module, "get_current_theme", lambda: "morandi")
    palette = get_chart_palette("morandi")

    df = pd.DataFrame({"date": ["2026-05-01", "2026-05-02"], "close": [100.0, 101.0], "change": [1.0, -1.0]})
    spark = build_index_sparkline(df, "加權指數")
    bars = build_bar_chart(df, "date", "change", "漲跌")

    assert spark.data[0].line.color == palette.MORANDI_UP
    assert list(bars.data[0].marker.color) == [palette.MORANDI_UP, palette.MORANDI_DOWN]


def test_backtest_visualizer_uses_shared_palette(monkeypatch):
    import src.ui.theme.plotly_template as plotly_module

    monkeypatch.setattr(plotly_module, "get_current_theme", lambda: "morandi")
    palette = get_chart_palette("morandi")

    df = pd.DataFrame({
        "date": ["2026-05-01", "2026-05-02"],
        "forward_date": ["2026-05-06", "2026-05-07"],
        "forward_return_pct": [2.0, -1.0],
    })

    equity = build_equity_curve(df)
    returns = build_return_distribution(df)

    assert equity.layout.paper_bgcolor == palette.BACKGROUND
    assert equity.data[0].line.color == palette.BLUE
    assert list(returns.data[0].marker.color) == [palette.MORANDI_UP, palette.MORANDI_DOWN]


def test_news_card_uses_theme_tokens(monkeypatch):
    import src.ui.components.news_card as module

    captured = []

    monkeypatch.setattr(module, "get_current_theme", lambda: "morandi")
    monkeypatch.setattr(module.st, "html", lambda html: captured.append(html))
    monkeypatch.setattr(module.st, "caption", lambda _text: None)

    module.render_news_section([], {"score": 0.7, "label": "positive", "article_count": 2})
    tokens = get_tokens("morandi")

    assert tokens["semantic_up_text"] in captured[0]
    assert tokens["text_secondary"] in captured[0]
