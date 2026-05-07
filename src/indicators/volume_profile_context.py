from __future__ import annotations

import pandas as pd

from src.indicators.volume_profile import compute_volume_profile


def poc_distance_pct(close: float, poc_price: float) -> float:
    """Percentage distance from close to POC. Positive = close above POC."""
    if poc_price <= 0:
        return 0.0
    return round((close - poc_price) / poc_price * 100, 2)


def is_in_support_zone(close: float, top_zones: list[dict], tolerance_pct: float = 2.0) -> bool:
    """True if close is within tolerance_pct% of any top volume zone."""
    for zone in top_zones:
        price = float(zone.get("price", 0))
        if price <= 0:
            continue
        if abs(close - price) / price * 100 <= tolerance_pct:
            return True
    return False


def summarize_vp_context(df: pd.DataFrame, close: float | None = None) -> dict:
    """Return POC distance and support-zone status for the latest close."""
    profile = compute_volume_profile(df, n_days=60, n_bins=20)
    poc = profile.get("poc_price")
    top_zones = profile.get("top_zones", [])

    if close is None and not df.empty and "close" in df.columns:
        close = float(pd.to_numeric(df["close"], errors="coerce").dropna().iloc[-1])

    if close is None or poc is None:
        return {
            "poc_price": poc,
            "poc_distance_pct": None,
            "in_support_zone": False,
            "nearest_zone_price": None,
            "nearest_zone_distance_pct": None,
        }

    dist = poc_distance_pct(close, poc)
    in_zone = is_in_support_zone(close, top_zones)

    nearest_price: float | None = None
    nearest_dist: float | None = None
    if top_zones:
        closest = min(top_zones, key=lambda z: abs(float(z.get("price", 0)) - close))
        nearest_price = float(closest["price"])
        nearest_dist = round((close - nearest_price) / nearest_price * 100, 2) if nearest_price > 0 else None

    return {
        "poc_price": poc,
        "poc_distance_pct": dist,
        "in_support_zone": in_zone,
        "nearest_zone_price": nearest_price,
        "nearest_zone_distance_pct": nearest_dist,
    }
