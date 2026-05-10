from __future__ import annotations

import pandas as pd

from src.indicators.estimated_delta import compute_delta_profile

_COLOR_BUY = "#6A9E8A"   # Morandi green — net buying pressure
_COLOR_SELL = "#C87D6A"  # Morandi red   — net selling pressure
_COLOR_FLAT = "#8A8480"  # Morandi grey  — neutral / doji

_X_LEFT = 0.78   # paper-coord left edge of overlay (right 22% of chart)
_X_RIGHT = 0.995  # paper-coord right edge


def build_delta_profile_overlay(
    df: pd.DataFrame,
    n_days: int = 60,
    n_bins: int = 20,
) -> tuple[list[dict], list[dict]]:
    """Plotly shapes + annotations for a delta-colored Volume Profile overlay.

    Each price bin is rendered as a horizontal bar on the right side of the
    chart (paper x: 0.78–1.0).  Bar length is proportional to bin volume;
    colour reflects Estimated Bar Delta sign (green = buying, red = selling).
    POC (peak volume) gets a text label.

    Returns (shapes, annotations) ready for fig.update_layout().
    """
    profile = compute_delta_profile(df, n_days=n_days, n_bins=n_bins)
    bins: list[float] = profile.get("bins", [])
    volumes: list[float] = profile.get("volumes", [])
    deltas: list[float] = profile.get("deltas", [])
    poc_price: float | None = profile.get("poc_price")

    if not bins:
        return [], []

    max_vol = max((v for v in volumes if v > 0), default=1.0)
    bar_span = _X_RIGHT - _X_LEFT

    shapes: list[dict] = []
    annotations: list[dict] = []

    for price, vol, delta in zip(bins, volumes, deltas):
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
                "width": 2.5 if is_poc else 1.8,
                "dash": "solid",
            },
            "opacity": 0.88 if is_poc else 0.55,
        })

        if is_poc:
            annotations.append({
                "x": _X_RIGHT,
                "y": price,
                "xref": "paper",
                "yref": "y",
                "xanchor": "left",
                "showarrow": False,
                "text": f"POC {price:.2f}",
                "font": {"color": color, "size": 10},
            })

    return shapes, annotations
