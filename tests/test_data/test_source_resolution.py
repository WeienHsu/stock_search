from src.data.source_resolution import fetch_with_source_fallback


def test_fetch_with_source_fallback_uses_next_candidate_after_failure():
    failures = []

    def fetch(source):
        if source == "first":
            raise RuntimeError("down")
        return [source]

    result = fetch_with_source_fallback(
        ["first", "second"],
        fetch,
        lambda value: bool(value),
        empty_result=[],
        on_failure=lambda source, reason: failures.append((source, reason)),
    )

    assert result == ["second"]
    assert failures == [("first", "down")]


def test_fetch_with_source_fallback_returns_empty_result_when_all_fail():
    result = fetch_with_source_fallback(
        ["first", "second"],
        lambda source: [],
        lambda value: bool(value),
        empty_result=[],
    )

    assert result == []
