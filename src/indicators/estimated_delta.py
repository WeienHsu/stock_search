from __future__ import annotations

import numpy as np
import pandas as pd


def compute_bar_delta(row: pd.Series) -> float:
    """Estimated Bar Delta: volume × (2×close − high − low) / (high − low).

    Positive → net buying pressure; negative → net selling pressure.
    Returns 0.0 for doji bars (high == low) to avoid division by zero.
    """
    high = float(row.get("high") or 0)
    low = float(row.get("low") or 0)
    close = float(row.get("close") or 0)
    volume = float(row.get("volume") or 0)
    span = high - low
    if span <= 0:
        return 0.0
    return volume * (2 * close - high - low) / span


def compute_delta_profile(
    df: pd.DataFrame,
    n_days: int = 60,
    n_bins: int = 20,
) -> dict:
    """Volume profile extended with Estimated Bar Delta per price bin.

    Returns dict with keys:
      bins       — list of bin center prices
      volumes    — total volume per bin
      deltas     — net estimated delta per bin (+ buy / − sell)
      poc_price  — price of maximum volume bin
      top_zones  — top-3 volume bins, each with price / volume / delta
    """
    required = {"high", "low", "close", "volume"}
    if df.empty or not required.issubset(df.columns):
        return {"bins": [], "volumes": [], "deltas": [], "poc_price": None, "top_zones": []}

    data = df.tail(n_days).copy()
    prices = pd.to_numeric(data["close"], errors="coerce")
    volumes = pd.to_numeric(data["volume"], errors="coerce").fillna(0)
    deltas = data.apply(compute_bar_delta, axis=1)

    if prices.dropna().empty or volumes.sum() <= 0:
        return {"bins": [], "volumes": [], "deltas": [], "poc_price": None, "top_zones": []}

    low = float(pd.to_numeric(data["low"], errors="coerce").min())
    high = float(pd.to_numeric(data["high"], errors="coerce").max())
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return {"bins": [], "volumes": [], "deltas": [], "poc_price": None, "top_zones": []}

    edges = np.linspace(low, high, n_bins + 1)
    price_arr = prices.to_numpy(dtype=float)

    hist_vol, bin_edges = np.histogram(price_arr, bins=edges, weights=volumes.to_numpy(dtype=float))
    hist_delta, _ = np.histogram(price_arr, bins=edges, weights=deltas.to_numpy(dtype=float))

    centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).round(4)
    hist_vol = hist_vol.astype(float)
    hist_delta = hist_delta.astype(float)

    poc_idx = int(hist_vol.argmax())
    top_indices = hist_vol.argsort()[-3:][::-1]

    return {
        "bins": centers.tolist(),
        "volumes": hist_vol.round(2).tolist(),
        "deltas": hist_delta.round(2).tolist(),
        "poc_price": float(centers[poc_idx]),
        "top_zones": [
            {
                "price": float(centers[idx]),
                "volume": float(hist_vol[idx]),
                "delta": float(hist_delta[idx]),
            }
            for idx in top_indices
            if hist_vol[idx] > 0
        ],
    }
