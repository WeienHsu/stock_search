from __future__ import annotations

import pandas as pd

from src.indicators.estimated_delta import compute_delta_profile

_COLOR_BUY = "#6A9E8A"    # Morandi green — net buying pressure
_COLOR_SELL = "#C87D6A"   # Morandi red   — net selling pressure
_COLOR_FLAT = "#8A8480"   # Morandi grey  — neutral / doji
_COLOR_LVN = "#B8A898"    # Morandi warm grey — low volume node

_X_LEFT = 0.78
_X_RIGHT = 0.995

_TOP_HVN = 5   # top-5 highest-volume bins (High Volume Nodes)


def build_delta_profile_overlay(
    df: pd.DataFrame,
    n_days: int = 60,
    n_bins: int = 20,
) -> tuple[list[dict], list[dict]]:
    """VP overlay: top-5 HVN (delta-colored) + 1 LVN (dashed).

    HVN (High Volume Node) = price levels where most trades occurred.
    LVN (Low Volume Node)  = price level where volume is thinnest within
                             the HVN price range; price tends to move
                             through LVNs quickly.

    Visual encoding:
    - HVN bar length ∝ volume; color = delta sign (green/red/grey)
    - POC (highest HVN) gets thicker line and explicit "POC" prefix
    - LVN rendered as a short dashed line at fixed 30% width
    - All bars carry a price label for immediate readability
    """
    profile = compute_delta_profile(df, n_days=n_days, n_bins=n_bins)
    bins: list[float] = profile.get("bins", [])
    volumes: list[float] = profile.get("volumes", [])
    deltas: list[float] = profile.get("deltas", [])
    poc_price: float | None = profile.get("poc_price")

    if not bins:
        return [], []

    all_bins = list(zip(bins, volumes, deltas))

    # ── Top-5 HVN ────────────────────────────────────────────────────────────
    hvn_sorted = sorted(all_bins, key=lambda t: t[1], reverse=True)
    hvn_top = [(p, v, d) for p, v, d in hvn_sorted[:_TOP_HVN] if v > 0]

    if not hvn_top:
        return [], []

    max_vol = hvn_top[0][1] or 1.0
    bar_span = _X_RIGHT - _X_LEFT

    # ── LVN: lowest-volume bin within the HVN price range ────────────────────
    hvn_prices = [p for p, _, _ in hvn_top]
    price_lo, price_hi = min(hvn_prices), max(hvn_prices)
    hvn_price_set = set(hvn_prices)

    lvn_candidate = min(
        (
            (p, v, d) for p, v, d in all_bins
            if v > 0 and price_lo <= p <= price_hi and p not in hvn_price_set
        ),
        key=lambda t: t[1],
        default=None,
    )

    shapes: list[dict] = []
    annotations: list[dict] = []

    # ── Render HVN bars ───────────────────────────────────────────────────────
    for price, vol, delta in hvn_top:
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
                "width": 3.2 if is_poc else 2.0,
                "dash": "solid",
            },
            "opacity": 0.92 if is_poc else 0.70,
        })
        annotations.append({
            "x": _X_RIGHT,
            "y": price,
            "xref": "paper",
            "yref": "y",
            "xanchor": "left",
            "showarrow": False,
            "text": ("POC " if is_poc else "") + f"{price:.2f}",
            "font": {"color": color, "size": 10},
        })

    # ── Render LVN marker ─────────────────────────────────────────────────────
    if lvn_candidate is not None:
        lvn_price, _, _ = lvn_candidate
        lvn_x1 = _X_LEFT + 0.30 * bar_span  # fixed short bar — volume is thin
        shapes.append({
            "type": "line",
            "xref": "paper",
            "yref": "y",
            "x0": _X_LEFT,
            "x1": lvn_x1,
            "y0": lvn_price,
            "y1": lvn_price,
            "line": {
                "color": _COLOR_LVN,
                "width": 1.4,
                "dash": "dash",
            },
            "opacity": 0.60,
        })
        annotations.append({
            "x": _X_RIGHT,
            "y": lvn_price,
            "xref": "paper",
            "yref": "y",
            "xanchor": "left",
            "showarrow": False,
            "text": f"LVN {lvn_price:.2f}",
            "font": {"color": _COLOR_LVN, "size": 9},
        })

    return shapes, annotations
