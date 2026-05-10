from src.repositories import ticker_resolution_repo


class FakeBackend:
    def __init__(self):
        self.data = {}

    def get(self, user_id, key, default=None):
        return self.data.get((user_id, key), default)

    def save(self, user_id, key, value):
        self.data[(user_id, key)] = value

    def delete(self, user_id, key):
        self.data.pop((user_id, key), None)


def test_ticker_resolution_repo_persists_suffix_by_user(monkeypatch):
    backend = FakeBackend()
    monkeypatch.setattr(ticker_resolution_repo, "_backend", backend)

    ticker_resolution_repo.save_ticker_resolution("3081", "3081.TWO", user_id="u1")
    ticker_resolution_repo.save_ticker_resolution("3081", "3081.TW", user_id="u2")

    assert ticker_resolution_repo.get_resolved_ticker("3081.TW", user_id="u1") == "3081.TWO"
    assert ticker_resolution_repo.get_resolved_ticker("3081.TW", user_id="u2") == "3081.TW"
    assert ticker_resolution_repo.get_resolved_ticker("3081.TW", user_id="u3") is None


def test_ticker_resolution_repo_ignores_unsupported_tickers(monkeypatch):
    backend = FakeBackend()
    monkeypatch.setattr(ticker_resolution_repo, "_backend", backend)

    ticker_resolution_repo.save_ticker_resolution("TSLA", "TSLA", user_id="u1")

    assert ticker_resolution_repo.get_resolved_ticker("TSLA", user_id="u1") is None
