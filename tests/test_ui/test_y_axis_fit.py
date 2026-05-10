"""Tests for src/ui/charts/_y_axis_fit.py"""
from __future__ import annotations

import json
import re

import pytest

from src.ui.charts._y_axis_fit import build_post_script


DATES = ["2024-01-02", "2024-01-03", "2024-01-04"]
LOWS  = [10.0, 11.0, 10.5]
HIGHS = [12.0, 13.0, 12.5]


# ── Output structure ──────────────────────────────────────────────────────────

def test_returns_string():
    out = build_post_script("myDiv", DATES, LOWS, HIGHS, [])
    assert isinstance(out, str)


def test_iife_wrapper():
    out = build_post_script("myDiv", DATES, LOWS, HIGHS, [])
    assert out.strip().startswith("(function()")
    assert out.strip().endswith("})();")


def test_div_id_embedded_correctly():
    out = build_post_script("test-chart-42", DATES, LOWS, HIGHS, [])
    assert '"test-chart-42"' in out


def test_div_id_json_escaped():
    # Div ID with special chars must be JSON-escaped, not raw
    out = build_post_script('div"quote', DATES, LOWS, HIGHS, [])
    assert json.dumps('div"quote') in out


def test_dates_embedded():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert '"2024-01-02"' in out
    assert '"2024-01-03"' in out


def test_lows_highs_embedded():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "10.0" in out
    assert "13.0" in out


def test_none_values_serialised_as_null():
    lows_with_none  = [None, 11.0, 10.5]
    highs_with_none = [12.0, None, 12.5]
    out = build_post_script("d", DATES, lows_with_none, highs_with_none, [])
    assert "null" in out


# ── Sub-panel embedding ───────────────────────────────────────────────────────

def test_macd_panel_type_embedded():
    panels = [{"type": "macd", "axis": "yaxis2", "valueArrays": [[1.0, 2.0, 3.0]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    assert '"macd"' in out
    assert '"yaxis2"' in out


def test_bias_panel_type_embedded():
    panels = [{"type": "bias", "axis": "yaxis3", "valueArrays": [[-2.0, 0.0, 2.0]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    assert '"bias"' in out
    assert '"yaxis3"' in out


def test_volume_panel_type_embedded():
    panels = [{"type": "volume", "axis": "yaxis4", "valueArrays": [[100, 200, 300]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    assert '"volume"' in out
    assert '"yaxis4"' in out


def test_multiple_sub_panels():
    panels = [
        {"type": "macd",   "axis": "yaxis2", "valueArrays": [[1.0, 2.0]]},
        {"type": "volume", "axis": "yaxis3", "valueArrays": [[500, 600]]},
    ]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    assert '"macd"'   in out
    assert '"volume"' in out


def test_empty_sub_panels():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    # subPanels should be an empty array
    assert "subPanels  = []" in out or '"subPanels"' not in out
    assert re.search(r"subPanels\s*=\s*\[\s*\]", out)


# ── JavaScript landmarks ──────────────────────────────────────────────────────

def test_contains_fitall_function():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "function fitAll()" in out


def test_contains_axisrange_function():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "function axisRange()" in out


def test_contains_plotly_relayout_event():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "plotly_relayout" in out


def test_contains_plotly_doubleclick_event():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "plotly_doubleclick" in out


def test_contains_resize_event():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert 'window.addEventListener("resize"' in out


def test_contains_settimeout_initial_fit():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "setTimeout" in out


def test_uses_request_animation_frame():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    assert "requestAnimationFrame" in out


def test_single_relayout_call_in_fitall():
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    # fitAll should collect all updates and call Plotly.relayout once
    assert "Plotly.relayout(gd, updates)" in out


# ── Panel-specific JS rules ───────────────────────────────────────────────────

def test_macd_keeps_zero_visible_in_js():
    panels = [{"type": "macd", "axis": "yaxis2", "valueArrays": [[1.0]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    # The JS should contain logic to keep 0 in MACD range
    assert "-pad" in out or "Math.min(vMin" in out


def test_bias_symmetric_in_js():
    panels = [{"type": "bias", "axis": "yaxis3", "valueArrays": [[1.5]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    # bias section must negate the abs value for lo
    assert '=== "bias"' in out or "bias" in out
    assert "-abs" in out


def test_volume_starts_at_zero_in_js():
    panels = [{"type": "volume", "axis": "yaxis4", "valueArrays": [[1000]]}]
    out = build_post_script("d", DATES, LOWS, HIGHS, panels)
    assert "lo = 0" in out


# ── KD exclusion ─────────────────────────────────────────────────────────────

def test_kd_not_in_output_when_excluded():
    # KD range is fixed [0,100]; build_post_script intentionally has no KD handling
    out = build_post_script("d", DATES, LOWS, HIGHS, [])
    # No hardcoded kd type reference should appear
    assert '"kd"' not in out
