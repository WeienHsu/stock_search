from __future__ import annotations

import pytest

from src.data.exchange_mapper import ticker_to_tv_symbol
from src.ui.components.tradingview_chart import _build_widget_url


# ── ticker_to_tv_symbol ───────────────────────────────────────────────────────


def test_tw_maps_to_tpe():
    assert ticker_to_tv_symbol("2330.TW") == "TPE:2330"


def test_two_maps_to_tpex():
    assert ticker_to_tv_symbol("6271.TWO") == "TPEX:6271"


def test_us_stock_passthrough():
    assert ticker_to_tv_symbol("TSLA") == "TSLA"


def test_lowercase_normalized():
    assert ticker_to_tv_symbol("tsla") == "TSLA"
    assert ticker_to_tv_symbol("2330.tw") == "TPE:2330"


def test_five_digit_tw():
    assert ticker_to_tv_symbol("00631L.TW") == "TPE:00631L"


def test_leading_trailing_spaces():
    assert ticker_to_tv_symbol("  2330.TW  ") == "TPE:2330"


# ── _build_widget_url ─────────────────────────────────────────────────────────


def test_url_contains_symbol():
    url = _build_widget_url("TPE:2330")
    assert "TPE" in url
    assert "2330" in url


def test_url_contains_theme_light():
    url = _build_widget_url("TSLA", theme="light")
    assert "theme=light" in url


def test_url_contains_theme_dark():
    url = _build_widget_url("TSLA", theme="dark")
    assert "theme=dark" in url


def test_url_contains_locale_zh():
    url = _build_widget_url("TSLA")
    assert "zh_TW" in url


def test_url_contains_timezone_taipei():
    url = _build_widget_url("TSLA")
    assert "Taipei" in url


def test_url_interval_default_daily():
    url = _build_widget_url("TSLA")
    assert "interval=D" in url


def test_url_interval_weekly():
    url = _build_widget_url("TSLA", interval="W")
    assert "interval=W" in url


def test_url_starts_with_tradingview_base():
    url = _build_widget_url("TSLA")
    assert url.startswith("https://s.tradingview.com/widgetembed/")


# ── render_tradingview_chart (smoke) ──────────────────────────────────────────


def test_render_calls_iframe(monkeypatch):
    import src.ui.components.tradingview_chart as tv_mod

    calls: list[dict] = []

    def _fake_iframe(url: str, *, height: int) -> None:
        calls.append({"url": url, "height": height})

    monkeypatch.setattr(tv_mod.st, "iframe", _fake_iframe)
    monkeypatch.setattr(tv_mod.st, "caption", lambda *a, **kw: None)

    tv_mod.render_tradingview_chart("2330.TW")

    assert len(calls) == 1
    assert "TPE" in calls[0]["url"]
    assert calls[0]["height"] == 620


def test_render_uses_correct_symbol_for_us(monkeypatch):
    import src.ui.components.tradingview_chart as tv_mod

    calls: list[dict] = []
    monkeypatch.setattr(tv_mod.st, "iframe", lambda url, **kw: calls.append(url))
    monkeypatch.setattr(tv_mod.st, "caption", lambda *a, **kw: None)

    tv_mod.render_tradingview_chart("TSLA")

    assert len(calls) == 1
    assert "TSLA" in calls[0]
    assert "TPE" not in calls[0]
