from __future__ import annotations

import pandas as pd

from src.indicators.estimated_delta import compute_delta_profile
from src.ui.theme.plotly_template import get_chart_palette

_X_LEFT = 0.78
_X_RIGHT = 0.995
_LABEL_X = 1.01

_TOP_HVN = 3   # POC + VP2 + VP3 highest-volume bins
_CURRENT_PRICE_NEAR_PCT = 1.0


def build_delta_profile_overlay(
    df: pd.DataFrame,
    n_days: int = 60,
    n_bins: int = 20,
    *,
    current_price: float | None = None,
    show_delta: bool = False,
) -> tuple[list[dict], list[dict]]:
    """VP overlay: POC/VP2/VP3 cost zones + optional Estimated Delta labels.

    HVN (High Volume Node) = price levels where most trades occurred.
    LVN (Low Volume Node)  = price level where volume is thinnest within
                             the HVN price range; price tends to move
                             through LVNs quickly.

    Visual encoding:
    - HVN bar length ∝ volume; color follows latest price position
    - POC (highest HVN) gets stronger line and explicit "POC" prefix
    - VP2 / VP3 mark the next two highest-volume price zones
    - If current_price is provided, labels describe relative location
    - LVN rendered as a short dashed line at fixed 30% width
    - show_delta=True appends Estimated Delta wording to labels
    """
    profile = compute_delta_profile(df, n_days=n_days, n_bins=n_bins)
    bins: list[float] = profile.get("bins", [])
    volumes: list[float] = profile.get("volumes", [])
    deltas: list[float] = profile.get("deltas", [])
    poc_price: float | None = profile.get("poc_price")

    if not bins:
        return [], []

    all_bins = list(zip(bins, volumes, deltas))

    # ── Top HVN zones: POC + VP2 + VP3 ───────────────────────────────────────
    hvn_sorted = sorted(all_bins, key=lambda t: t[1], reverse=True)
    hvn_top = [(p, v, d) for p, v, d in hvn_sorted[:_TOP_HVN] if v > 0]

    if not hvn_top:
        return [], []

    palette = get_chart_palette()
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
    for rank, (price, vol, delta) in enumerate(hvn_top, start=1):
        is_poc = price == poc_price
        ratio = vol / max_vol
        x1 = _X_LEFT + ratio * bar_span
        color = _relative_line_color(price, current_price, palette)
        label = _hvn_label(rank, price, current_price=current_price, delta=delta, show_delta=show_delta)

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
                "width": 3.2 if is_poc else 2.4 if rank == 2 else 2.0,
                "dash": "solid",
            },
            "opacity": 0.92 if is_poc else 0.70,
        })
        annotations.append({
            "x": _LABEL_X,
            "y": price,
            "xref": "paper",
            "yref": "y",
            "xanchor": "left",
            "xshift": 4,
            "align": "left",
            "showarrow": False,
            "text": label,
            "font": {"color": color, "size": 10},
        })

    # ── Render LVN marker ─────────────────────────────────────────────────────
    if lvn_candidate is not None:
        lvn_price, _, _ = lvn_candidate
        lvn_x1 = _X_LEFT + 0.30 * bar_span  # fixed short bar — volume is thin
        lvn_color = _relative_line_color(lvn_price, current_price, palette)
        shapes.append({
            "type": "line",
            "xref": "paper",
            "yref": "y",
            "x0": _X_LEFT,
            "x1": lvn_x1,
            "y0": lvn_price,
            "y1": lvn_price,
            "line": {
                "color": lvn_color,
                "width": 1.4,
                "dash": "dash",
            },
            "opacity": 0.60,
        })
        annotations.append({
            "x": _LABEL_X,
            "y": lvn_price,
            "xref": "paper",
            "yref": "y",
            "xanchor": "left",
            "xshift": 4,
            "align": "left",
            "showarrow": False,
            "text": f"LVN {lvn_price:.2f}",
            "font": {"color": lvn_color, "size": 9},
        })

    return shapes, annotations


def _hvn_label(
    rank: int,
    price: float,
    *,
    current_price: float | None,
    delta: float,
    show_delta: bool,
) -> str:
    prefix = "POC" if rank == 1 else f"VP{rank}"
    parts = [f"{prefix} {price:.2f}"]
    zone = _relative_zone_label(price, current_price)
    if zone:
        parts.append(zone)
    if show_delta:
        parts.append(_delta_label(delta))
    return " · ".join(parts)


def _relative_zone_label(price: float, current_price: float | None) -> str:
    if current_price is None or current_price <= 0:
        return ""
    diff_pct = (price - current_price) / current_price * 100
    if abs(diff_pct) <= _CURRENT_PRICE_NEAR_PCT:
        return "現價附近"
    if diff_pct < 0:
        return "下方成本區"
    return "上方成交區"


def _relative_line_color(price: float, current_price: float | None, palette) -> str:
    if current_price is None or current_price <= 0:
        return palette.TEXT_SECONDARY
    if current_price >= price:
        return palette.MORANDI_UP
    return palette.MORANDI_DOWN


def _delta_label(delta: float) -> str:
    if delta > 0:
        return "估算買壓"
    if delta < 0:
        return "估算賣壓"
    return "中性"
