import pandas as pd

from src.indicators.volume_profile import compute_volume_profile


def test_compute_volume_profile_returns_poc_and_top_zones():
    df = pd.DataFrame({
        "high": [10, 11, 12, 13],
        "low": [9, 10, 11, 12],
        "close": [9.5, 10.5, 11.5, 12.5],
        "volume": [100, 500, 200, 100],
    })

    result = compute_volume_profile(df, n_days=4, n_bins=4)

    assert len(result["bins"]) == 4
    assert result["poc_price"] is not None
    assert result["top_zones"][0]["volume"] == 500.0
