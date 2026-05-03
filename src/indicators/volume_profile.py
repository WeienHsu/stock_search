from __future__ import annotations

import numpy as np
import pandas as pd


def compute_volume_profile(df: pd.DataFrame, n_days: int = 60, n_bins: int = 20) -> dict:
    if df.empty or not {"high", "low", "close", "volume"}.issubset(df.columns):
        return {"bins": [], "volumes": [], "poc_price": None, "top_zones": []}

    data = df.tail(n_days).copy()
    prices = pd.to_numeric(data["close"], errors="coerce")
    volumes = pd.to_numeric(data["volume"], errors="coerce").fillna(0)
    if prices.dropna().empty or volumes.sum() <= 0:
        return {"bins": [], "volumes": [], "poc_price": None, "top_zones": []}

    low = float(pd.to_numeric(data["low"], errors="coerce").min())
    high = float(pd.to_numeric(data["high"], errors="coerce").max())
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return {"bins": [], "volumes": [], "poc_price": None, "top_zones": []}

    edges = np.linspace(low, high, n_bins + 1)
    hist, bin_edges = np.histogram(prices.to_numpy(dtype=float), bins=edges, weights=volumes.to_numpy(dtype=float))
    centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).round(4)
    hist = hist.astype(float)
    poc_idx = int(hist.argmax()) if len(hist) else 0
    top_indices = hist.argsort()[-3:][::-1] if len(hist) else []

    return {
        "bins": centers.tolist(),
        "volumes": hist.round(2).tolist(),
        "poc_price": float(centers[poc_idx]) if len(centers) else None,
        "top_zones": [
            {"price": float(centers[idx]), "volume": float(hist[idx])}
            for idx in top_indices
            if hist[idx] > 0
        ],
    }
