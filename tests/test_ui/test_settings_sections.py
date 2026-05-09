from pathlib import Path

from src.ui.pages.settings.ai_api_section import AI_PROVIDERS


def test_api_settings_sections_stay_small():
    base = Path("src/ui/pages/settings")

    assert _line_count(base / "market_api_section.py") < 80
    assert _line_count(base / "ai_api_section.py") < 80


def test_ai_api_section_keeps_expected_providers():
    assert [provider[0] for provider in AI_PROVIDERS] == ["Anthropic", "Gemini", "OpenAI"]


def _line_count(path: Path) -> int:
    return len(path.read_text().splitlines())
