"""Option B — Top-N with Delta: show only the 7 highest-volume bins.

Keeps the original "sparse and clean" philosophy but replaces fixed-width
lines with proportional bars and adds delta coloring.  Each bin gets an
explicit price label so the user can read exact levels at a glance.
"""
from __future__ import annotations

import pandas as pd

from src.indicators.estimated_delta import compute_delta_profile

_COLOR_BUY = "#6A9E8A"   # Morandi green — net buying pressure
_COLOR_SELL = "#C87D6A"  # Morandi red   — net selling pressure
_COLOR_FLAT = "#8A8480"  # Morandi grey  — neutral / doji

_X_LEFT = 0.78
_X_RIGHT = 0.995

_TOP_N = 7   # only the 7 highest-volume bins are shown


def build_delta_profile_overlay(
    df: pd.DataFrame,
    n_days: int = 60,
    n_bins: int = 20,
) -> tuple[list[dict], list[dict]]:
    """Sparse VP overlay: top-7 bins by volume, delta-colored, all labeled.

    Each bin is a horizontal bar whose:
    - Length  ∝ volume (standard VP look)
    - Color   = delta sign (green buy / red sell / grey flat)
    - Label   = price shown on every bar (not just POC)

    Only shows the _TOP_N most significant price levels, keeping
    the chart uncluttered while still communicating delta direction.
    """
    profile = compute_delta_profile(df, n_days=n_days, n_bins=n_bins)
    bins: list[float] = profile.get("bins", [])
    volumes: list[float] = profile.get("volumes", [])
    deltas: list[float] = profile.get("deltas", [])
    poc_price: float | None = profile.get("poc_price")

    if not bins:
        return [], []

    # Select top-N bins by volume
    indexed = sorted(
        enumerate(zip(bins, volumes, deltas)),
        key=lambda x: x[1][1],
        reverse=True,
    )[:_TOP_N]

    max_vol = max(v for _, (_, v, _) in indexed) or 1.0
    bar_span = _X_RIGHT - _X_LEFT

    shapes: list[dict] = []
    annotations: list[dict] = []

    for _, (price, vol, delta) in indexed:
        if vol <= 0:
            continue

        is_poc = price == poc_price
        ratio = vol / max_vol
        x1 = _X_LEFT + ratio * bar_span

        if delta > 0:
            color = _COLOR_BUY
        elif delta < 0:
            color = _COLOR_SELL
        else:
            color = _COLOR_FLAT

        shapes.append({
            "type": "line",
            "xref": "paper",
            "yref": "y",
            "x0": _X_LEFT,
            "x1": x1,
            "y0": price,
            "y1": price,
            "line": {
                "color": color,
                "width": 3.0 if is_poc else 1.8,
                "dash": "solid",
            },
            "opacity": 0.90 if is_poc else 0.65,
        })

        label = ("POC " if is_poc else "") + f"{price:.2f}"
        annotations.append({
            "x": _X_RIGHT,
            "y": price,
            "xref": "paper",
            "yref": "y",
            "xanchor": "left",
            "showarrow": False,
            "text": label,
            "font": {"color": color, "size": 10},
        })

    return shapes, annotations
