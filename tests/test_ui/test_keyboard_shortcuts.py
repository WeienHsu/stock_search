from src.ui.nav import keyboard_shortcuts


def test_shortcut_script_contains_required_shortcuts():
    script = keyboard_shortcuts._shortcut_script()

    assert 'key === "/"' in script
    assert '"d": "dashboard"' in script
    assert '"s": "dashboard"' in script
    assert 'input[placeholder="輸入代號或名稱"]' in script
    assert "isTypingTarget(event.target)" in script
    assert "findNavLink(pageKey)" in script
    assert "link.click()" in script
    assert "window.location.assign" in script


def test_inject_shortcuts_uses_streamlit_html_with_javascript(monkeypatch):
    calls = []

    def fake_html(body, **kwargs):
        calls.append((body, kwargs))

    monkeypatch.setattr(keyboard_shortcuts.st, "html", fake_html)

    keyboard_shortcuts.inject_shortcuts()

    assert len(calls) == 1
    body, kwargs = calls[0]
    assert "<script>" in body
    assert kwargs == {"width": "content", "unsafe_allow_javascript": True}
