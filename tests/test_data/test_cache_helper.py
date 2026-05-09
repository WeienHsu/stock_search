from src.data import cache_helper


def test_clear_all_caches_clears_streamlit_and_repository_layers(monkeypatch):
    streamlit_calls = []
    repository_calls = []

    def fake_streamlit_clear():
        streamlit_calls.append("clear")

    def fake_repo_clearer(user_id: str) -> int:
        repository_calls.append(user_id)
        return 2 if user_id == "global" else 1

    monkeypatch.setattr(cache_helper.st.cache_data, "clear", fake_streamlit_clear)
    monkeypatch.setattr(
        cache_helper,
        "_REPOSITORY_CLEARERS",
        {"prices": fake_repo_clearer, "news": fake_repo_clearer},
    )

    result = cache_helper.clear_all_caches("local")

    assert streamlit_calls == ["clear"]
    assert repository_calls == ["global", "local", "global", "local"]
    assert result == {
        "streamlit": True,
        "repositories": {"prices": 3, "news": 3},
        "deleted_files": 6,
    }


def test_repository_user_ids_do_not_duplicate_global():
    assert cache_helper._repository_user_ids("global") == ["global"]
