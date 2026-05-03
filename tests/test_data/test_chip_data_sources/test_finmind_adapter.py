import pandas as pd

from src.data.chip_data_sources.finmind_adapter import FinMindChipDataSource, _clean_token


def test_clean_token_strips_double_equal_typo_in_dotenv():
    # `KEY==xxx` in .env is parsed by python-dotenv as value "=xxx", which
    # FinMind rejects with HTTP 400. Clean it defensively.
    assert _clean_token("=eyJabc.def") == "eyJabc.def"
    assert _clean_token("  =eyJabc.def  ") == "eyJabc.def"
    assert _clean_token('"=eyJabc.def"') == "eyJabc.def"
    assert _clean_token("eyJabc.def") == "eyJabc.def"
    assert _clean_token("") == ""
    assert _clean_token(None) == ""  # type: ignore[arg-type]


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


def test_finmind_institutional_frame_ignores_unmapped_rows():
    adapter = FinMindChipDataSource()

    df = adapter._institutional_frame([
        {"date": "2026-04-30", "name": "Unknown", "buy": 3000, "sell": 1000},
    ])

    assert df.empty


def test_finmind_shareholding_snapshot_requires_ratio():
    adapter = FinMindChipDataSource()

    snapshot = adapter._shareholding_snapshot([
        {"date": "2026-04-30", "stock_id": "2330"},
    ])

    assert snapshot == {}


def test_finmind_shareholding_snapshot_extracts_shares_and_history():
    adapter = FinMindChipDataSource()

    snapshot = adapter._shareholding_snapshot([
        {
            "date": "2026-03-31",
            "stock_id": "00981A",
            "stock_name": "主動統一台股增長",
            "ForeignInvestmentSharesRatio": 3.0,
            "ForeignInvestmentRemainRatio": 97.0,
            "ForeignInvestmentShares": 100_000_000,
            "ForeignInvestmentRemainingShares": 3_000_000_000,
            "NumberOfSharesIssued": 3_100_000_000,
            "ForeignInvestmentUpperLimitRatio": 100.0,
        },
        {
            "date": "2026-04-30",
            "stock_id": "00981A",
            "stock_name": "主動統一台股增長",
            "ForeignInvestmentSharesRatio": 4.44,
            "ForeignInvestmentRemainRatio": 95.55,
            "ForeignInvestmentShares": 376_206_028,
            "ForeignInvestmentRemainingShares": 8_091_502_972,
            "NumberOfSharesIssued": 8_467_709_000,
            "ForeignInvestmentUpperLimitRatio": 100.0,
        },
    ])

    assert snapshot["foreign_holding_pct"] == 4.44
    assert snapshot["foreign_holding_pct_prev"] == 3.0
    assert snapshot["foreign_holding_change_pp"] == 1.44
    assert snapshot["foreign_holding_shares"] == 376_206_028
    assert snapshot["shares_issued"] == 8_467_709_000
    assert snapshot["foreign_upper_limit_pct"] == 100.0
    assert snapshot["stock_name"] == "主動統一台股增長"
    assert len(snapshot["history"]) == 2
    assert snapshot["history"][-1] == {"date": "2026-04-30", "foreign_holding_pct": 4.44}


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


def test_finmind_monthly_revenue_marks_etf_unsupported_without_chip_health():
    adapter = FinMindChipDataSource()

    result = adapter.fetch_monthly_revenue("0050.TW", 12)

    assert result.source_status.source_id == "revenue_finmind"
    assert result.source_status.status == "unsupported"
