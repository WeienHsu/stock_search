import pytest

from src.ui.pages.onboarding_page import (
    ATR_MULTIPLIER_BY_RISK,
    INDUSTRY_OPTIONS,
    MARKET_OPTIONS,
    RISK_OPTIONS,
    _clear_draft,
    _save_completed,
    is_onboarding_complete,
)


# ── Constants ─────────────────────────────────────────────────────────────────

def test_market_options_include_both():
    assert "台股" in MARKET_OPTIONS
    assert "美股" in MARKET_OPTIONS
    assert "兩者" in MARKET_OPTIONS


def test_risk_options_have_three_levels():
    assert len(RISK_OPTIONS) == 3
    assert "保守" in RISK_OPTIONS
    assert "中性" in RISK_OPTIONS
    assert "積極" in RISK_OPTIONS


def test_atr_multiplier_increases_with_risk():
    assert ATR_MULTIPLIER_BY_RISK["保守"] < ATR_MULTIPLIER_BY_RISK["中性"]
    assert ATR_MULTIPLIER_BY_RISK["中性"] < ATR_MULTIPLIER_BY_RISK["積極"]


def test_industry_options_are_non_empty():
    assert len(INDUSTRY_OPTIONS) >= 5
    assert "半導體" in INDUSTRY_OPTIONS


# ── is_onboarding_complete ────────────────────────────────────────────────────

def test_is_onboarding_complete_returns_false_when_no_prefs(tmp_path):
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository
    import src.repositories.user_prefs_repo as _up_module

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)

    original = _up_module._repo
    _up_module._repo = repo
    try:
        assert not is_onboarding_complete("test-user")
    finally:
        _up_module._repo = original


def test_is_onboarding_complete_returns_true_after_save(tmp_path):
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository
    import src.repositories.user_prefs_repo as _up_module

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)
    repo.set("user-1", "onboarding", {"completed": True, "skipped": False})

    original = _up_module._repo
    _up_module._repo = repo
    try:
        assert is_onboarding_complete("user-1")
        assert not is_onboarding_complete("user-other")
    finally:
        _up_module._repo = original


# ── _clear_draft ──────────────────────────────────────────────────────────────

def test_clear_draft_removes_session_keys(monkeypatch):
    import streamlit as st
    monkeypatch.setitem(st.session_state, "_onboarding_step", 3)
    monkeypatch.setitem(st.session_state, "_onboarding_draft", {"market": "台股"})

    _clear_draft()

    assert "_onboarding_step" not in st.session_state
    assert "_onboarding_draft" not in st.session_state


# ── _save_completed ───────────────────────────────────────────────────────────

def test_save_completed_persists_onboarding_flag(tmp_path, monkeypatch):
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository
    import src.repositories.user_prefs_repo as _up_module
    import streamlit as st

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)

    monkeypatch.setitem(st.session_state, "_onboarding_draft", {
        "market": "台股",
        "risk": "積極",
        "industries": ["半導體"],
    })

    original = _up_module._repo
    _up_module._repo = repo
    try:
        _save_completed("user-1", skipped=False)
        prefs = repo.get("user-1", "onboarding")
        assert prefs["completed"] is True
        assert prefs["skipped"] is False
        assert prefs["market"] == "台股"
        assert prefs["risk"] == "積極"
        assert "半導體" in prefs["industries"]
    finally:
        _up_module._repo = original


def test_save_completed_skipped_still_marks_complete(tmp_path, monkeypatch):
    from src.repositories._backends.json_backend import JsonBackend
    from src.repositories.user_prefs_repo import UserPreferencesRepository
    import src.repositories.user_prefs_repo as _up_module
    import streamlit as st

    backend = JsonBackend(base_dir=tmp_path)
    repo = UserPreferencesRepository(backend)

    monkeypatch.setitem(st.session_state, "_onboarding_draft", {})

    original = _up_module._repo
    _up_module._repo = repo
    try:
        _save_completed("user-2", skipped=True)
        prefs = repo.get("user-2", "onboarding")
        assert prefs["completed"] is True
        assert prefs["skipped"] is True
    finally:
        _up_module._repo = original
