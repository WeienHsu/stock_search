from __future__ import annotations

import pandas as pd
import pytest

from src.indicators.estimated_delta import compute_bar_delta, compute_delta_profile


# ── compute_bar_delta ─────────────────────────────────────────────────────────


def _row(high, low, close, volume):
    return pd.Series({"high": high, "low": low, "close": close, "volume": volume})


def test_bar_delta_close_at_high_is_positive():
    # close == high → maximum buying pressure
    delta = compute_bar_delta(_row(high=10, low=8, close=10, volume=1000))
    assert delta > 0


def test_bar_delta_close_at_low_is_negative():
    # close == low → maximum selling pressure
    delta = compute_bar_delta(_row(high=10, low=8, close=8, volume=1000))
    assert delta < 0


def test_bar_delta_close_at_midpoint_is_zero():
    # close == midpoint → neutral
    delta = compute_bar_delta(_row(high=10, low=8, close=9, volume=1000))
    assert delta == pytest.approx(0.0, abs=1e-9)


def test_bar_delta_doji_returns_zero():
    # high == low → no span, no delta
    delta = compute_bar_delta(_row(high=10, low=10, close=10, volume=500))
    assert delta == 0.0


def test_bar_delta_formula_value():
    # delta = 1000 × (2×9.5 − 10 − 8) / (10 − 8) = 1000 × 1 / 2 = 500
    delta = compute_bar_delta(_row(high=10, low=8, close=9.5, volume=1000))
    assert delta == pytest.approx(500.0, abs=0.01)


def test_bar_delta_zero_volume():
    delta = compute_bar_delta(_row(high=10, low=8, close=9, volume=0))
    assert delta == 0.0


def test_bar_delta_none_values_treated_as_zero():
    row = pd.Series({"high": None, "low": None, "close": None, "volume": None})
    delta = compute_bar_delta(row)
    assert delta == 0.0


# ── compute_delta_profile ─────────────────────────────────────────────────────


def _make_df(n=10):
    base = 100.0
    return pd.DataFrame({
        "high": [base + i + 1 for i in range(n)],
        "low": [base + i - 1 for i in range(n)],
        "close": [base + i + 0.5 for i in range(n)],  # skewed toward high → positive delta
        "volume": [1_000.0] * n,
    })


def test_delta_profile_keys():
    result = compute_delta_profile(_make_df(), n_bins=5)
    assert set(result.keys()) == {"bins", "volumes", "deltas", "poc_price", "top_zones"}


def test_delta_profile_bin_count():
    result = compute_delta_profile(_make_df(), n_bins=10)
    assert len(result["bins"]) == 10
    assert len(result["volumes"]) == 10
    assert len(result["deltas"]) == 10


def test_delta_profile_positive_deltas_when_close_near_high():
    # close is always near high → all deltas should be positive
    result = compute_delta_profile(_make_df(), n_bins=5)
    non_zero_deltas = [d for d in result["deltas"] if d != 0]
    assert all(d > 0 for d in non_zero_deltas)


def test_delta_profile_negative_deltas_when_close_near_low():
    n = 10
    base = 100.0
    df = pd.DataFrame({
        "high": [base + i + 1 for i in range(n)],
        "low": [base + i - 1 for i in range(n)],
        "close": [base + i - 0.5 for i in range(n)],  # skewed toward low
        "volume": [1_000.0] * n,
    })
    result = compute_delta_profile(df, n_bins=5)
    non_zero_deltas = [d for d in result["deltas"] if d != 0]
    assert all(d < 0 for d in non_zero_deltas)


def test_delta_profile_poc_price_is_valid():
    result = compute_delta_profile(_make_df(), n_bins=5)
    assert result["poc_price"] is not None
    assert result["poc_price"] in result["bins"]


def test_delta_profile_top_zones_have_delta_key():
    result = compute_delta_profile(_make_df(), n_bins=5)
    for zone in result["top_zones"]:
        assert "delta" in zone


def test_delta_profile_empty_df():
    result = compute_delta_profile(pd.DataFrame(), n_bins=5)
    assert result["bins"] == []
    assert result["poc_price"] is None


def test_delta_profile_missing_columns():
    df = pd.DataFrame({"close": [100, 101]})
    result = compute_delta_profile(df, n_bins=5)
    assert result["bins"] == []


def test_delta_profile_zero_volume_df():
    df = _make_df()
    df["volume"] = 0
    result = compute_delta_profile(df, n_bins=5)
    assert result["bins"] == []


# ── build_delta_profile_overlay ───────────────────────────────────────────────


def test_overlay_returns_shapes_and_annotations():
    from src.ui.charts.volume_profile import build_delta_profile_overlay

    shapes, annotations = build_delta_profile_overlay(_make_df(), n_bins=5)
    assert isinstance(shapes, list)
    assert isinstance(annotations, list)
    assert len(shapes) > 0


def test_overlay_poc_annotation_present():
    from src.ui.charts.volume_profile import build_delta_profile_overlay

    _, annotations = build_delta_profile_overlay(_make_df(), n_bins=5)
    poc_labels = [a for a in annotations if "POC" in str(a.get("text", ""))]
    assert len(poc_labels) == 1


def test_overlay_empty_df_returns_empty():
    from src.ui.charts.volume_profile import build_delta_profile_overlay

    shapes, annotations = build_delta_profile_overlay(pd.DataFrame(), n_bins=5)
    assert shapes == []
    assert annotations == []


def test_overlay_shapes_use_paper_coords():
    from src.ui.charts.volume_profile import build_delta_profile_overlay

    shapes, _ = build_delta_profile_overlay(_make_df(), n_bins=5)
    for s in shapes:
        assert s["xref"] == "paper"
        assert s["x0"] == pytest.approx(0.78, abs=0.01)
