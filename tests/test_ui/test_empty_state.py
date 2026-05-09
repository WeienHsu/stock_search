from src.ui.components.empty_state import _icon_html, _slug


def test_empty_state_named_icon_renders_svg():
    html = _icon_html("search")

    assert "<svg" in html
    assert "empty-state-icon" in html


def test_empty_state_unknown_icon_is_escaped():
    html = _icon_html("<bad>")

    assert "&lt;bad&gt;" in html


def test_empty_state_action_key_slug_is_stable():
    assert _slug("前往 設定!") == "前往_設定"
