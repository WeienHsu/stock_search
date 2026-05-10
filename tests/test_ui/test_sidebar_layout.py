from pathlib import Path


def test_sidebar_removes_empty_divider_widgets():
    app_source = Path("app.py").read_text(encoding="utf-8")
    sidebar_source = Path("src/ui/sidebar.py").read_text(encoding="utf-8")

    assert "st.sidebar.divider()" not in app_source
    assert "st.sidebar.divider()" not in sidebar_source
    assert "sidebar-section-rule" not in app_source
    assert "sidebar-section-rule" not in sidebar_source


def test_sidebar_markdown_background_is_transparent():
    source = Path("src/ui/theme/styles.py").read_text(encoding="utf-8")

    assert '[data-testid="stSidebar"] .stMarkdown' in source
    assert '[data-testid="stSidebar"] [data-testid="stElementContainer"]' in source
    assert "background-color: transparent !important;" in source
