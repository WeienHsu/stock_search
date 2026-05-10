import pandas as pd
import pytest

from src.ui.pages.settings.holdings_section import _df_to_holdings, _holdings_to_df


def test_holdings_to_df_returns_correct_columns():
    items = [
        {"ticker": "2330.TW", "quantity": 1000.0, "avg_cost": 850.0},
        {"ticker": "TSLA", "quantity": 10.0, "avg_cost": 200.0},
    ]
    df = _holdings_to_df(items)

    assert list(df.columns) == ["ticker", "quantity", "avg_cost"]
    assert len(df) == 2
    assert df.iloc[0]["ticker"] == "2330.TW"


def test_holdings_to_df_empty_returns_empty_dataframe():
    df = _holdings_to_df([])

    assert df.empty
    assert list(df.columns) == ["ticker", "quantity", "avg_cost"]


def test_df_to_holdings_converts_valid_rows():
    df = pd.DataFrame({
        "ticker": ["2330.TW", "AAPL"],
        "quantity": [500.0, 20.0],
        "avg_cost": [900.0, 180.0],
    })
    items = _df_to_holdings(df)

    assert len(items) == 2
    assert items[0]["ticker"] == "2330.TW"
    assert items[0]["quantity"] == 500.0
    assert items[0]["avg_cost"] == 900.0


def test_df_to_holdings_skips_empty_ticker():
    df = pd.DataFrame({
        "ticker": ["", "MSFT"],
        "quantity": [100.0, 50.0],
        "avg_cost": [10.0, 300.0],
    })
    items = _df_to_holdings(df)

    assert len(items) == 1
    assert items[0]["ticker"] == "MSFT"


def test_df_to_holdings_skips_zero_quantity_and_cost():
    df = pd.DataFrame({
        "ticker": ["A", "B", "C"],
        "quantity": [0.0, 100.0, 100.0],
        "avg_cost": [10.0, 0.0, 50.0],
    })
    items = _df_to_holdings(df)

    assert len(items) == 1
    assert items[0]["ticker"] == "C"


def test_df_to_holdings_uppercases_ticker():
    df = pd.DataFrame({
        "ticker": ["tsla"],
        "quantity": [10.0],
        "avg_cost": [200.0],
    })
    items = _df_to_holdings(df)

    assert items[0]["ticker"] == "TSLA"


def test_df_to_holdings_handles_none_dataframe():
    assert _df_to_holdings(None) == []


def test_df_to_holdings_handles_empty_dataframe():
    assert _df_to_holdings(pd.DataFrame()) == []
