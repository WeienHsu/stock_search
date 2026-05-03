from src.repositories import chip_data_cache_repo


class MemoryBackend:
    def __init__(self):
        self.values = {}
        self.fresh = True

    def is_fresh(self, user_id, key, ttl_seconds):
        self.last_ttl = ttl_seconds
        return self.fresh and (user_id, key) in self.values

    def get(self, user_id, key):
        return self.values.get((user_id, key))

    def save(self, user_id, key, value):
        self.values[(user_id, key)] = value


def test_chip_cache_uses_ttl_override(monkeypatch):
    backend = MemoryBackend()
    backend.save("global", "k", {"ok": True})
    monkeypatch.setattr(chip_data_cache_repo, "_backend", backend)

    assert chip_data_cache_repo.get_chip_cache("k", ttl_override=123) == {"ok": True}
    assert backend.last_ttl == 123
