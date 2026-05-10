from __future__ import annotations

from datetime import date

import pytest

from src.scheduler.jobs.daily_digest import (
    PRE_MARKET,
    POST_MARKET,
    _enabled_types,
    run_daily_digest,
)


# ── _enabled_types ────────────────────────────────────────────────────────────


def test_enabled_types_defaults_to_pre_market_only():
    prefs = {"enabled": True}
    types = _enabled_types(prefs)
    assert PRE_MARKET in types
    assert POST_MARKET not in types


def test_enabled_types_both_when_set():
    prefs = {"pre_market": True, "post_market": True}
    types = _enabled_types(prefs)
    assert PRE_MARKET in types
    assert POST_MARKET in types


def test_enabled_types_neither_when_both_false():
    prefs = {"pre_market": False, "post_market": False}
    assert _enabled_types(prefs) == set()


# ── run_daily_digest ──────────────────────────────────────────────────────────


def test_run_daily_digest_skips_when_disabled(tmp_path, monkeypatch):
    import src.repositories.user_prefs_repo as _up
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "digest_settings", {"enabled": False})
    monkeypatch.setattr(_up, "_repo", repo)

    result = run_daily_digest("user-1", PRE_MARKET)

    assert result["skipped"] is True
    assert result["reason"] == "disabled"


def test_run_daily_digest_skips_when_type_disabled(tmp_path, monkeypatch):
    import src.repositories.user_prefs_repo as _up
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "digest_settings", {"enabled": True, "pre_market": False, "post_market": False})
    monkeypatch.setattr(_up, "_repo", repo)

    result = run_daily_digest("user-1", PRE_MARKET)

    assert result["skipped"] is True
    assert "disabled" in result["reason"]


def test_run_daily_digest_skips_if_already_sent_today(tmp_path, monkeypatch):
    import src.repositories.user_prefs_repo as _up
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository

    today = str(date.today())
    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "digest_settings", {"enabled": True, "pre_market": True})
    repo.set("user-1", "digest_cache", {PRE_MARKET: {"date": today}})
    monkeypatch.setattr(_up, "_repo", repo)

    result = run_daily_digest("user-1", PRE_MARKET)

    assert result["skipped"] is True
    assert result["reason"] == "already_sent_today"


def test_run_daily_digest_sends_and_caches(tmp_path, monkeypatch):
    import src.repositories.user_prefs_repo as _up
    import src.scheduler.jobs.daily_digest as dd_mod
    from src.notifications.base import NotificationResult
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "digest_settings", {"enabled": True, "pre_market": True})
    monkeypatch.setattr(_up, "_repo", repo)

    # Stub run_digest and send_notification
    monkeypatch.setattr(dd_mod, "run_digest", lambda uid, dtype: ("AI 摘要內容", True))
    monkeypatch.setattr(
        dd_mod,
        "send_notification",
        lambda uid, subject, body, **kw: [NotificationResult("inbox", True)],
    )

    result = run_daily_digest("user-1", PRE_MARKET)

    assert result["skipped"] is False
    assert result["delivered"] is True
    assert result["used_ai"] is True
    assert "inbox" in result["channels"]

    # Verify cache was written
    cache = repo.get("user-1", "digest_cache")
    assert cache[PRE_MARKET]["date"] == str(date.today())


def test_run_daily_digest_fallback_still_caches_on_failed_delivery(tmp_path, monkeypatch):
    import src.repositories.user_prefs_repo as _up
    import src.scheduler.jobs.daily_digest as dd_mod
    from src.notifications.base import NotificationResult
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "digest_settings", {"enabled": True, "pre_market": True})
    monkeypatch.setattr(_up, "_repo", repo)

    monkeypatch.setattr(dd_mod, "run_digest", lambda uid, dtype: ("fallback 文字", False))
    monkeypatch.setattr(
        dd_mod,
        "send_notification",
        lambda uid, subject, body, **kw: [NotificationResult("email", False, "SMTP error")],
    )

    result = run_daily_digest("user-1", PRE_MARKET)

    assert result["skipped"] is False
    assert result["delivered"] is False
    # Cache still written to avoid retry spam
    cache = repo.get("user-1", "digest_cache")
    assert PRE_MARKET in cache
