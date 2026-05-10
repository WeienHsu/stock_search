from src.ui.nav.command_palette import (
    _client_palette_payload,
    _command_palette_controller_script,
    _command_palette_markup,
    build_command_sections,
    page_command_results,
)
from src.ui.nav.keyboard_shortcuts import _shortcut_script
from src.ui.nav.ticker_index import build_ticker_index, default_watchlist_matches, fuzzy_ticker_matches


def test_ticker_index_matches_symbol_name_and_alias():
    index = build_ticker_index(
        [{"ticker": "TSLA", "name": "Tesla custom"}],
        [{"ticker": "TSLA", "name": "Tesla default"}, {"ticker": "2330.TW", "name": "台積電"}],
    )

    assert fuzzy_ticker_matches("ts", index)[0].ticker == "TSLA"
    assert fuzzy_ticker_matches("台積", index)[0].ticker == "2330.TW"
    assert fuzzy_ticker_matches("tsmc", index)[0].ticker == "2330.TW"


def test_empty_query_returns_watchlist_first_ten():
    index = build_ticker_index(
        [{"ticker": f"23{i:02d}.TW", "name": f"股票{i}"} for i in range(12)],
        [{"ticker": "TSLA", "name": "Tesla"}],
    )

    matches = default_watchlist_matches(index, limit=10)

    assert len(matches) == 10
    assert matches[0].ticker == "2300.TW"
    assert all(match.source == "watchlist" for match in matches)


def test_command_sections_group_tickers_and_pages():
    sections = build_command_sections(
        "scanner",
        [{"ticker": "TSLA", "name": "Tesla"}],
        [{"ticker": "2330.TW", "name": "台積電"}],
    )

    assert "Pages" in sections
    assert sections["Pages"][0].page_key == "scanner"


def test_command_sections_show_pages_only_when_query_is_blank():
    sections = build_command_sections(
        "",
        [{"ticker": "TSLA", "name": "Tesla"}],
        [{"ticker": "2330.TW", "name": "台積電"}],
    )

    assert "Watchlist" not in sections
    assert "Tickers" not in sections
    assert any(result.page_key == "today" for result in sections["Pages"])


def test_page_command_results_match_path_and_label():
    assert page_command_results("settings")[0].page_key == "settings"
    assert page_command_results("回測")[0].page_key == "backtest"


def test_keyboard_shortcuts_include_cmd_k_without_removing_existing_shortcuts():
    script = _shortcut_script()

    assert 'key === "k"' in script
    assert 'stock-search:open-command-palette' in script
    assert "cmdk" not in script
    assert 'key === "/"' in script
    assert 'key === "g"' in script


def test_client_palette_payload_contains_ticker_aliases_and_pages():
    payload = _client_palette_payload(
        [],
        [{"ticker": "2330.TW", "name": "台積電"}],
    )

    assert payload["tickers"][0]["ticker"] == "2330.TW"
    assert "tsmc" in payload["tickers"][0]["aliases"]
    assert any(page["pageKey"] == "settings" for page in payload["pages"])


def test_client_command_palette_overlay_does_not_need_query_param():
    markup = _command_palette_markup({"tickers": [], "pages": []})
    script = _command_palette_controller_script()

    assert "data-command-palette-payload" in markup
    assert "stock-search-command-palette" in script
    assert "window.addEventListener(\"stock-search:open-command-palette\"" in script
    assert "url.searchParams.set(\"page\"" in script
    assert "cmdk" not in script
    assert "${" not in script
