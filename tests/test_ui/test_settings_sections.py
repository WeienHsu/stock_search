from pathlib import Path

from src.ui.pages.settings.ai_api_section import AI_PROVIDERS


def test_api_settings_sections_stay_small():
    base = Path("src/ui/pages/settings")

    assert _line_count(base / "market_api_section.py") < 80
    assert _line_count(base / "ai_api_section.py") < 80


def test_ai_api_section_keeps_expected_providers():
    assert [provider[0] for provider in AI_PROVIDERS] == ["Anthropic", "Gemini", "OpenAI"]


def test_volume_profile_delta_preference_is_available_but_default_off():
    preferences_source = Path("src/ui/pages/settings/preferences_section.py").read_text(encoding="utf-8")
    repo_source = Path("src/repositories/preferences_repo.py").read_text(encoding="utf-8")
    sidebar_source = Path("src/ui/sidebar.py").read_text(encoding="utf-8")

    assert '"show_volume_profile_delta": False' in repo_source
    assert "settings_show_volume_profile_delta" in preferences_source
    assert '"show_volume_profile_delta": show_volume_profile_delta' in preferences_source
    assert 'st.session_state["_preferences_saved"] = True' in preferences_source
    assert "st.rerun()" in preferences_source
    assert '"show_volume_profile_delta": show_volume_profile_delta' in sidebar_source


def _line_count(path: Path) -> int:
    return len(path.read_text().splitlines())
