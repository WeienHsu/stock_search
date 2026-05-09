from src.ui.components.today_holdings_summary import build_holdings_summary


def test_build_holdings_summary_calculates_unrealized_pnl():
    summary = build_holdings_summary([
        {"ticker": "2330.TW", "quantity": 10, "avg_cost": 100, "current_price": 110},
        {"ticker": "TSLA", "shares": 2, "cost_basis": 200, "market_price": 190},
    ])

    assert summary == {
        "count": 2,
        "total_cost": 1400.0,
        "market_value": 1480.0,
        "unrealized_pnl": 80.0,
        "unrealized_pnl_pct": 5.71,
    }


def test_build_holdings_summary_ignores_missing_or_invalid_holdings():
    assert build_holdings_summary(None)["count"] == 0
    assert build_holdings_summary([{"ticker": "2330.TW", "quantity": 10}])["count"] == 0
