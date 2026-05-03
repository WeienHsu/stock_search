from src.ui.components.sidebar_search import build_search_candidates, format_candidate, fuzzy_ticker_matches


def test_build_search_candidates_deduplicates_watchlist_before_defaults():
    candidates = build_search_candidates(
        [{"ticker": "tsla", "name": "Tesla custom"}],
        [{"ticker": "TSLA", "name": "Tesla default"}, {"ticker": "2330", "name": "台積電"}],
    )

    assert {"ticker": "TSLA", "name": "Tesla custom"} in candidates
    assert {"ticker": "2330.TW", "name": "台積電"} in candidates


def test_fuzzy_ticker_matches_symbol_and_name():
    candidates = [
        {"ticker": "TSLA", "name": "Tesla"},
        {"ticker": "2330.TW", "name": "台積電"},
        {"ticker": "GOOGL", "name": "Alphabet"},
    ]

    assert fuzzy_ticker_matches("ts", candidates)[0]["ticker"] == "TSLA"
    assert fuzzy_ticker_matches("台積", candidates)[0]["ticker"] == "2330.TW"
    assert format_candidate(candidates[0]) == "TSLA — Tesla"
