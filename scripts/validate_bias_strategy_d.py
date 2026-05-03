from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.bias_strategy_d_validation import (
    CandidateSpec,
    ValidationConfig,
    add_prior_oversold_counts,
    build_event_dataset,
    by_ticker_metrics,
    current_specs,
    evaluate_specs_across_splits,
    load_cached_price_data,
    load_default_settings,
    load_user_context,
    merge_strategy_d_params,
    optimize_candidates,
    render_markdown_report,
    select_best_primary_candidate,
    verdict_for_selected,
    write_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate whether prior BIAS oversold events improve Strategy D buy signals."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--user-id", default=None, help="User id to load from data/users.db or data/users/.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/bias_strategy_d_validation"),
        help="Directory for generated Markdown and CSV outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    config = ValidationConfig()
    defaults = load_default_settings(root)
    context = load_user_context(root, user_id=args.user_id)
    strategy_params = merge_strategy_d_params(defaults, context.get("preferences", {}))

    prices, skipped = load_cached_price_data(root, context.get("watchlist", []))
    dataset, ticker_summary = build_event_dataset(
        prices,
        strategy_params=strategy_params,
        periods=config.periods,
        forward_days=config.forward_days,
    )
    if dataset.empty:
        raise SystemExit("No cached price data could be loaded for validation.")

    dataset = add_prior_oversold_counts(
        dataset,
        periods=config.periods,
        thresholds=config.thresholds,
        pre_days_values=config.pre_days,
    )

    current_metrics = evaluate_specs_across_splits(dataset, current_specs(config), config)
    candidate_results = optimize_candidates(dataset, config)
    selected_spec = select_best_primary_candidate(candidate_results, config)

    if selected_spec is None:
        selected_metrics = pd.DataFrame()
        selected_by_ticker = pd.DataFrame()
        verdict = "do_not_implement"
    else:
        selected_horizon_specs = [
            CandidateSpec(
                period=selected_spec.period,
                threshold=selected_spec.threshold,
                pre_days=selected_spec.pre_days,
                min_count=selected_spec.min_count,
                forward_days=days,
            )
            for days in config.forward_days
        ]
        selected_metrics = evaluate_specs_across_splits(dataset, selected_horizon_specs, config)
        selected_by_ticker = by_ticker_metrics(
            dataset,
            selected_spec,
            split="all",
            train_cutoff=config.train_cutoff,
        )
        verdict = verdict_for_selected(selected_metrics, config)

    report = render_markdown_report(
        context=context,
        strategy_params=strategy_params,
        ticker_summary=ticker_summary,
        skipped=skipped,
        current_metrics=current_metrics,
        candidate_results=candidate_results,
        selected_metrics=selected_metrics,
        selected_by_ticker=selected_by_ticker,
        selected_spec=selected_spec,
        verdict=verdict,
        config=config,
    )
    paths = write_outputs(
        output_dir,
        report,
        ticker_summary,
        current_metrics,
        candidate_results,
        selected_metrics,
        selected_by_ticker,
    )

    print(f"Report: {paths['report']}")
    print(f"Verdict: {verdict}")
    if selected_spec is not None:
        print(
            "Selected candidate: "
            f"period={selected_spec.period}, threshold={selected_spec.threshold}, "
            f"pre_days={selected_spec.pre_days}, min_count={selected_spec.min_count}, "
            f"rank_horizon={selected_spec.forward_days}"
        )
    print(f"Loaded tickers: {len(ticker_summary)}")
    print(f"Strategy D buy events: {int(ticker_summary['strategy_d_buy_events'].sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
