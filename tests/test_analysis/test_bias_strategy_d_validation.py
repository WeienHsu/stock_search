import pandas as pd

from src.analysis.bias_strategy_d_validation import (
    CandidateSpec,
    add_prior_oversold_counts,
    evaluate_candidate,
)


def _sample_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA"] * 6,
            "name": [""] * 6,
            "years_loaded": [10] * 6,
            "date": pd.date_range("2023-01-02", periods=6, freq="B").strftime("%Y-%m-%d"),
            "date_ts": pd.date_range("2023-01-02", periods=6, freq="B"),
            "close": [100, 95, 90, 92, 96, 98],
            "bias_20": [-1.0, -6.0, -7.0, -4.0, -8.0, -2.0],
            "return_2d_pct": [-10.0, -3.16, 6.67, 6.52, 2.08, None],
            "max_close_return_2d_pct": [0.0, -3.16, 6.67, 6.52, 2.08, None],
            "is_strategy_d_buy": [False, False, False, True, False, False],
        }
    )


def test_prior_oversold_counts_only_uses_days_before_signal():
    dataset = add_prior_oversold_counts(
        _sample_dataset(),
        periods=[20],
        thresholds=[-5.0],
        pre_days_values=[3],
    )

    signal_row = dataset.loc[dataset["date"] == "2023-01-05"].iloc[0]
    same_day_oversold_row = dataset.loc[dataset["date"] == "2023-01-06"].iloc[0]

    assert signal_row["prior_oversold_p20_t5p0_n3"] == 2
    assert same_day_oversold_row["prior_oversold_p20_t5p0_n3"] == 2


def test_evaluate_candidate_reports_lift_for_bias_strategy_d_subset():
    dataset = add_prior_oversold_counts(
        _sample_dataset(),
        periods=[20],
        thresholds=[-5.0],
        pre_days_values=[3],
    )
    result = evaluate_candidate(
        dataset,
        CandidateSpec(period=20, threshold=-5.0, pre_days=3, min_count=2, forward_days=2),
        split="all",
        train_cutoff="2024-01-01",
        effective_thresholds={2: 3.0},
    )

    assert result["strategy_d_events"] == 1
    assert result["bias_strategy_d_events"] == 1
    assert result["coverage_pct"] == 100.0
    assert result["bias_strategy_d_win_rate_pct"] == 100.0
    assert result["bias_strategy_d_effective_up_rate_pct"] == 100.0
    assert result["bias_strategy_d_touched_profit_rate_pct"] == 100.0
