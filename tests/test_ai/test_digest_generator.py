from __future__ import annotations

import pandas as pd
import pytest

from src.ai.digest_generator import _fallback_digest, build_digest_rows, run_digest
from src.ai.prompts.daily_digest import (
    build_post_market_messages,
    build_pre_market_messages,
    generate_daily_digest,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_df(close_prices: list[float]) -> pd.DataFrame:
    n = len(close_prices)
    return pd.DataFrame({
        "date": [f"2026-05-{i + 1:02d}" for i in range(n)],
        "open": close_prices,
        "high": [p + 1 for p in close_prices],
        "low": [p - 1 for p in close_prices],
        "close": close_prices,
        "volume": [1_000_000] * n,
    })


class FakeChain:
    def __init__(self, response: str = "AI 摘要內容", *, fail: bool = False):
        self.response = response
        self.fail = fail
        self.calls: list[tuple] = []

    def generate(self, messages, system="", temperature=0.2) -> str:
        self.calls.append((messages, system))
        if self.fail:
            raise RuntimeError("AI unavailable")
        return self.response


# ── Prompt builders ───────────────────────────────────────────────────────────


def test_pre_market_messages_contain_payload():
    rows = [{"ticker": "2330.TW", "close": 900.0, "day_change_pct": 1.5}]
    msgs = build_pre_market_messages(rows)

    assert len(msgs) == 1
    assert "2330.TW" in msgs[0]["content"]
    assert "盤前" in msgs[0]["content"]


def test_post_market_messages_contain_payload():
    rows = [{"ticker": "TSLA", "close": 200.0, "day_change_pct": -2.0}]
    msgs = build_post_market_messages(rows)

    assert "TSLA" in msgs[0]["content"]
    assert "盤後" in msgs[0]["content"]


def test_generate_daily_digest_pre_market_calls_chain():
    chain = FakeChain("盤前 AI 回應")
    rows = [{"ticker": "0050.TW", "close": 150.0, "day_change_pct": 0.5}]

    result = generate_daily_digest(chain, rows, "pre_market")

    assert result == "盤前 AI 回應"
    assert len(chain.calls) == 1
    assert "盤前" in chain.calls[0][0][0]["content"]


def test_generate_daily_digest_post_market_calls_chain():
    chain = FakeChain("盤後 AI 回應")
    rows = [{"ticker": "0050.TW", "close": 150.0, "day_change_pct": 0.5}]

    result = generate_daily_digest(chain, rows, "post_market")

    assert "盤後" in chain.calls[0][0][0]["content"]


# ── build_digest_rows ─────────────────────────────────────────────────────────


def test_build_digest_rows_extracts_price_and_change(monkeypatch):
    import src.ai.digest_generator as gen_mod

    df = _make_df([100.0, 102.0, 105.0])
    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [{"ticker": "TSLA", "name": "Tesla"}])

    rows = build_digest_rows("user-1", _price_fn=lambda t, p: df)

    assert len(rows) == 1
    assert rows[0]["ticker"] == "TSLA"
    assert rows[0]["close"] == 105.0
    assert abs(rows[0]["day_change_pct"] - 2.94) < 0.1


def test_build_digest_rows_handles_empty_df(monkeypatch):
    import src.ai.digest_generator as gen_mod

    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [{"ticker": "BAD", "name": ""}])

    rows = build_digest_rows("user-1", _price_fn=lambda t, p: pd.DataFrame())

    assert rows[0].get("error") == "無資料"


def test_build_digest_rows_handles_fetch_exception(monkeypatch):
    import src.ai.digest_generator as gen_mod

    def _bad_fn(t, p):
        raise ConnectionError("network down")

    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [{"ticker": "X", "name": ""}])

    rows = build_digest_rows("user-1", _price_fn=_bad_fn)

    assert "error" in rows[0]


def test_build_digest_rows_empty_watchlist(monkeypatch):
    import src.ai.digest_generator as gen_mod

    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [])

    rows = build_digest_rows("user-1")

    assert rows == []


# ── run_digest ────────────────────────────────────────────────────────────────


def test_run_digest_returns_ai_content_when_chain_succeeds(monkeypatch):
    import src.ai.digest_generator as gen_mod

    df = _make_df([100.0, 102.0])
    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [{"ticker": "TSLA", "name": "Tesla"}])

    chain = FakeChain("AI 盤前摘要")
    content, used_ai = run_digest("user-1", "pre_market", chain=chain, _price_fn=lambda t, p: df)

    assert content == "AI 盤前摘要"
    assert used_ai is True


def test_run_digest_falls_back_when_ai_fails(monkeypatch):
    import src.ai.digest_generator as gen_mod

    df = _make_df([100.0, 105.0])
    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [{"ticker": "TSLA", "name": "Tesla"}])

    chain = FakeChain(fail=True)
    content, used_ai = run_digest("user-1", "pre_market", chain=chain, _price_fn=lambda t, p: df)

    assert used_ai is False
    assert "TSLA" in content


def test_run_digest_returns_empty_message_for_empty_watchlist(monkeypatch):
    import src.ai.digest_generator as gen_mod

    monkeypatch.setattr(gen_mod, "get_watchlist", lambda uid: [])

    content, used_ai = run_digest("user-1", "pre_market", chain=FakeChain())

    assert "自選清單為空" in content
    assert used_ai is False


# ── _fallback_digest ──────────────────────────────────────────────────────────


def test_fallback_digest_sorts_by_absolute_change():
    rows = [
        {"ticker": "A", "name": "A股", "close": 100.0, "day_change_pct": 1.0},
        {"ticker": "B", "name": "B股", "close": 50.0, "day_change_pct": -5.0},
        {"ticker": "C", "name": "C股", "close": 200.0, "day_change_pct": 3.0},
    ]
    result = _fallback_digest(rows, "pre_market")

    lines = result.split("\n")
    # B (−5%) should appear before A (+1%)
    b_idx = next(i for i, l in enumerate(lines) if "B" in l)
    a_idx = next(i for i, l in enumerate(lines) if "A" in l)
    assert b_idx < a_idx


def test_fallback_digest_no_valid_rows():
    rows = [{"ticker": "X", "name": "", "error": "無資料"}]
    result = _fallback_digest(rows, "post_market")

    assert "無可用資料" in result


def test_fallback_digest_title_matches_type():
    rows = [{"ticker": "A", "close": 100.0, "day_change_pct": 0.5, "name": ""}]
    pre = _fallback_digest(rows, "pre_market")
    post = _fallback_digest(rows, "post_market")

    assert "盤前" in pre
    assert "盤後" in post
