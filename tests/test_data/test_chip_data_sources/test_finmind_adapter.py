import pandas as pd

from src.data.chip_data_sources.finmind_adapter import FinMindChipDataSource


def test_finmind_institutional_frame_maps_english_investor_types():
    adapter = FinMindChipDataSource()
    df = adapter._institutional_frame([
        {"date": "2026-04-30", "name": "Foreign_Investor", "buy": 3000, "sell": 1000},
        {"date": "2026-04-30", "name": "Investment_Trust", "buy": 1000, "sell": 2000},
        {"date": "2026-04-30", "name": "Dealer_self", "buy": 500, "sell": 200},
        {"date": "2026-04-30", "name": "Dealer_Hedging", "buy": 100, "sell": 300},
        {"date": "2026-04-30", "name": "Foreign_Dealer_Self", "buy": 50, "sell": 0},
    ])

    row = df.iloc[0]

    assert row["foreign_net_lots"] == 2
    assert row["investment_trust_net_lots"] == -1
    assert row["dealer_net_lots"] == 0.15
    assert row["total_institutional_net_lots"] == 1.15


def test_finmind_monthly_revenue_marks_source_for_health_badge():
    adapter = FinMindChipDataSource()
    df = adapter._monthly_revenue_frame([
        {"date": "2026-04-01", "revenue": 415191699000, "revenue_month": 3, "revenue_year": 2026}
    ])

    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["source"] == "revenue_finmind"


def test_finmind_monthly_revenue_computes_yoy_when_missing():
    adapter = FinMindChipDataSource()
    df = adapter._monthly_revenue_frame([
        {"date": "2025-04-01", "revenue": 100, "revenue_month": 3, "revenue_year": 2025},
        {"date": "2026-04-01", "revenue": 125, "revenue_month": 3, "revenue_year": 2026},
    ])

    assert df.iloc[-1]["period"] == "2026-04"
    assert df.iloc[-1]["yoy_pct"] == 25.0
