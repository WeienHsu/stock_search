from pathlib import Path

from scripts.check_contrast import contrast_ratio
from src.ui.theme.tokens import get_tokens


def test_selected_tab_text_meets_wcag_aa_in_supported_themes():
    for theme in ("morandi", "dark"):
        tokens = get_tokens(theme)
        assert contrast_ratio(tokens["tab_selected_text"], tokens["bg_base"]) >= 4.5


def test_tab_css_targets_streamlit_inner_markdown_text():
    source = Path("src/ui/theme/styles.py").read_text(encoding="utf-8")

    assert "tab_selected_text" in source
    assert '[data-baseweb="tab"][aria-selected="true"] [data-testid="stMarkdownContainer"] p' in source
