from __future__ import annotations

import json
import pickle
import sqlite3
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.indicators.bias import add_bias
from src.strategies.strategy_d import StrategyD


@dataclass(frozen=True)
class CandidateSpec:
    period: int
    threshold: float
    pre_days: int
    min_count: int
    forward_days: int


@dataclass(frozen=True)
class ValidationConfig:
    periods: tuple[int, ...] = (10, 20, 30, 60)
    thresholds: tuple[float, ...] = (-3.0, -5.0, -7.0, -10.0)
    pre_days: tuple[int, ...] = (5, 10, 20, 30)
    min_counts: tuple[int, ...] = (1, 2, 3)
    forward_days: tuple[int, ...] = (5, 10, 20, 60)
    primary_forward_days: tuple[int, ...] = (5, 10)
    current_period: int = 20
    current_threshold: float = -5.0
    current_pre_days: int = 20
    current_min_count: int = 2
    train_cutoff: str = "2024-01-01"
    min_pattern_events: int = 30
    min_coverage_pct: float = 20.0
    min_tickers: int = 8
    min_primary_win_lift_pct: float = 5.0
    min_primary_mean_lift_pct: float = 0.5
    max_secondary_win_decline_pct: float = 3.0
    max_secondary_mean_decline_pct: float = 1.0


@dataclass(frozen=True)
class LoadedPriceData:
    ticker: str
    name: str
    years_loaded: int
    df: pd.DataFrame


def load_default_settings(root: Path) -> dict[str, Any]:
    with open(root / "config" / "default_settings.json", encoding="utf-8") as f:
        return json.load(f)


def load_user_context(root: Path, user_id: str | None = None) -> dict[str, Any]:
    defaults = load_default_settings(root)
    context: dict[str, Any] = {
        "source": "config/default_settings.json",
        "user_id": None,
        "watchlist": defaults.get("watchlist_defaults", []),
        "preferences": {},
    }

    db_path = root / "data" / "users.db"
    if db_path.exists():
        sqlite_context = _load_sqlite_context(db_path, user_id)
        if sqlite_context is not None:
            context.update(sqlite_context)
            return context

    json_context = _load_json_context(root / "data" / "users", user_id)
    if json_context is not None:
        context.update(json_context)

    return context


def _load_sqlite_context(db_path: Path, user_id: str | None) -> dict[str, Any] | None:
    query = """
        SELECT user_id, key, value, updated_at
        FROM kv_store
        WHERE key IN ('watchlist', 'preferences')
    """
    rows: list[tuple[str, str, str, float]]
    with sqlite3.connect(db_path) as conn:
        try:
            rows = conn.execute(query).fetchall()
        except sqlite3.Error:
            return None
    if not rows:
        return None

    grouped: dict[str, dict[str, Any]] = {}
    updated_at: dict[str, float] = {}
    for uid, key, value, ts in rows:
        if user_id and uid != user_id:
            continue
        grouped.setdefault(uid, {})[key] = json.loads(value)
        updated_at[uid] = max(updated_at.get(uid, 0.0), float(ts))

    candidates = [uid for uid, data in grouped.items() if data.get("watchlist")]
    if not candidates:
        return None
    selected = user_id if user_id in candidates else max(candidates, key=lambda uid: updated_at[uid])
    data = grouped[selected]
    return {
        "source": str(db_path),
        "user_id": selected,
        "watchlist": data.get("watchlist", []),
        "preferences": data.get("preferences", {}),
    }


def _load_json_context(users_dir: Path, user_id: str | None) -> dict[str, Any] | None:
    if not users_dir.exists():
        return None
    user_dirs = [users_dir / user_id] if user_id else sorted(p for p in users_dir.iterdir() if p.is_dir())
    newest: tuple[float, Path] | None = None
    for user_dir in user_dirs:
        watchlist_path = user_dir / "watchlist.json"
        if not watchlist_path.exists():
            continue
        mtime = watchlist_path.stat().st_mtime
        if newest is None or mtime > newest[0]:
            newest = (mtime, user_dir)
    if newest is None:
        return None

    selected_dir = newest[1]
    with open(selected_dir / "watchlist.json", encoding="utf-8") as f:
        watchlist = json.load(f)
    prefs_path = selected_dir / "preferences.json"
    preferences = {}
    if prefs_path.exists():
        with open(prefs_path, encoding="utf-8") as f:
            preferences = json.load(f)
    return {
        "source": str(selected_dir),
        "user_id": selected_dir.name,
        "watchlist": watchlist,
        "preferences": preferences,
    }


def merge_strategy_d_params(defaults: dict[str, Any], preferences: dict[str, Any]) -> dict[str, Any]:
    strategy_defaults = {
        **StrategyD().default_params(),
        **defaults.get("strategy_d", {}),
    }
    relevant_keys = set(strategy_defaults) | {
        key
        for key in preferences
        if key.startswith("buy_") or key.startswith("sell_")
    }
    overrides = {key: value for key, value in preferences.items() if key in relevant_keys}
    return {**strategy_defaults, **overrides}


def strategy_d_buy_param_summary(params: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "macd_fast",
        "macd_slow",
        "macd_signal",
        "kd_k",
        "kd_d",
        "kd_smooth_k",
        "buy_kd_window",
        "buy_n_bars",
        "buy_recovery_pct",
        "buy_kd_k_threshold",
        "buy_max_violations",
        "buy_lookback_bars",
    )
    return {key: params.get(key) for key in keys}


def load_cached_price_data(
    root: Path,
    watchlist: Iterable[dict[str, Any]],
    preferred_years: tuple[int, ...] = (10, 1),
) -> tuple[list[LoadedPriceData], list[dict[str, Any]]]:
    cache_dir = root / "data" / "cache" / "prices" / "global"
    loaded: list[LoadedPriceData] = []
    skipped: list[dict[str, Any]] = []

    for item in watchlist:
        ticker = str(item.get("ticker", "")).strip().upper()
        name = str(item.get("name", ""))
        if not ticker:
            skipped.append({"ticker": ticker, "name": name, "reason": "empty ticker"})
            continue

        match: tuple[int, Path] | None = None
        for years in preferred_years:
            path = cache_dir / f"{ticker}_{years}y.pkl"
            if path.exists():
                match = (years, path)
                break
        if match is None:
            skipped.append({"ticker": ticker, "name": name, "reason": "no cached price file"})
            continue

        years_loaded, path = match
        with open(path, "rb") as f:
            df = pickle.load(f)
        if not isinstance(df, pd.DataFrame) or df.empty:
            skipped.append({"ticker": ticker, "name": name, "reason": "empty cached dataframe"})
            continue
        if not {"date", "close", "high", "low"}.issubset(df.columns):
            skipped.append({"ticker": ticker, "name": name, "reason": "missing OHLC columns"})
            continue

        loaded.append(
            LoadedPriceData(
                ticker=ticker,
                name=name,
                years_loaded=years_loaded,
                df=df.copy().reset_index(drop=True),
            )
        )

    return loaded, skipped


def build_event_dataset(
    prices: Iterable[LoadedPriceData],
    strategy_params: dict[str, Any],
    periods: Iterable[int],
    forward_days: Iterable[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    ticker_rows: list[dict[str, Any]] = []
    strategy = StrategyD()

    for item in prices:
        df = item.df.copy().reset_index(drop=True)
        signals = strategy.compute(df, strategy_params)
        buy_dates = {signal.date[:10] for signal in signals if signal.signal_type == "buy"}

        event_df = df[["date", "close"]].copy()
        event_df["date"] = event_df["date"].astype(str).str[:10]
        for period in periods:
            event_df = add_bias(event_df, period=period)
        for days in forward_days:
            event_df[f"return_{days}d_pct"] = (
                (event_df["close"].shift(-days) - event_df["close"]) / event_df["close"] * 100
            )
            future_max_close = event_df["close"].shift(-1).rolling(days, min_periods=days).max().shift(-(days - 1))
            event_df[f"max_close_return_{days}d_pct"] = (
                (future_max_close - event_df["close"]) / event_df["close"] * 100
            )
        event_df["is_strategy_d_buy"] = event_df["date"].isin(buy_dates)
        event_df["ticker"] = item.ticker
        event_df["name"] = item.name
        event_df["years_loaded"] = item.years_loaded
        event_df["date_ts"] = pd.to_datetime(event_df["date"], errors="coerce")
        frames.append(event_df)

        ticker_rows.append(
            {
                "ticker": item.ticker,
                "name": item.name,
                "years_loaded": item.years_loaded,
                "first_date": event_df["date"].iloc[0],
                "last_date": event_df["date"].iloc[-1],
                "rows": len(event_df),
                "strategy_d_buy_events": len(buy_dates),
            }
        )

    if not frames:
        return pd.DataFrame(), pd.DataFrame(ticker_rows)

    dataset = pd.concat(frames, ignore_index=True)
    ticker_summary = pd.DataFrame(ticker_rows).sort_values("ticker").reset_index(drop=True)
    return dataset, ticker_summary


def add_prior_oversold_counts(
    dataset: pd.DataFrame,
    periods: Iterable[int],
    thresholds: Iterable[float],
    pre_days_values: Iterable[int],
) -> pd.DataFrame:
    out = dataset.copy()
    for period, threshold, pre_days in product(periods, thresholds, pre_days_values):
        bias_col = f"bias_{period}"
        count_col = prior_count_col(period, threshold, pre_days)
        out[count_col] = out.groupby("ticker", group_keys=False)[bias_col].transform(
            lambda series: (series <= threshold).shift(1).rolling(pre_days, min_periods=pre_days).sum()
        )
    return out


def prior_count_col(period: int, threshold: float, pre_days: int) -> str:
    threshold_token = str(abs(float(threshold))).replace(".", "p")
    return f"prior_oversold_p{period}_t{threshold_token}_n{pre_days}"


def iter_candidate_specs(config: ValidationConfig) -> Iterable[CandidateSpec]:
    for period, threshold, pre_days, min_count, forward_days in product(
        config.periods,
        config.thresholds,
        config.pre_days,
        config.min_counts,
        config.forward_days,
    ):
        yield CandidateSpec(period, threshold, pre_days, min_count, forward_days)


def evaluate_candidate(
    dataset: pd.DataFrame,
    spec: CandidateSpec,
    split: str,
    train_cutoff: str,
    effective_thresholds: dict[int, float] | None = None,
) -> dict[str, Any]:
    effective_thresholds = effective_thresholds or {5: 1.0, 10: 1.5, 20: 3.0, 60: 5.0}
    count_col = prior_count_col(spec.period, spec.threshold, spec.pre_days)
    return_col = f"return_{spec.forward_days}d_pct"
    max_return_col = f"max_close_return_{spec.forward_days}d_pct"
    if count_col not in dataset or return_col not in dataset or max_return_col not in dataset:
        raise KeyError(f"Dataset is missing {count_col}, {return_col}, or {max_return_col}.")

    df = dataset.dropna(subset=[count_col, return_col, max_return_col, "date_ts"]).copy()
    cutoff = pd.Timestamp(train_cutoff)
    if split == "train":
        df = df[(df["date_ts"] < cutoff) & (df["years_loaded"] > 1)]
    elif split == "test":
        df = df[df["date_ts"] >= cutoff]
    elif split != "all":
        raise ValueError("split must be one of: train, test, all")

    df["has_bias_pattern"] = df[count_col] >= spec.min_count
    strategy_d = df[df["is_strategy_d_buy"]]
    combined = strategy_d[strategy_d["has_bias_pattern"]]
    bias_only = df[(~df["is_strategy_d_buy"]) & df["has_bias_pattern"]]
    all_non_signal = df[~df["is_strategy_d_buy"]]
    threshold = effective_thresholds.get(spec.forward_days, 0.0)

    row: dict[str, Any] = {
        "split": split,
        "period": spec.period,
        "threshold": spec.threshold,
        "pre_days": spec.pre_days,
        "min_count": spec.min_count,
        "forward_days": spec.forward_days,
    }
    row.update(_prefixed_metrics("strategy_d", strategy_d, return_col, max_return_col, threshold))
    row.update(_prefixed_metrics("bias_strategy_d", combined, return_col, max_return_col, threshold))
    row.update(_prefixed_metrics("bias_only", bias_only, return_col, max_return_col, threshold))
    row.update(_prefixed_metrics("all_non_signal", all_non_signal, return_col, max_return_col, threshold))
    row["coverage_pct"] = _safe_pct(len(combined), len(strategy_d))
    row["ticker_count"] = int(combined["ticker"].nunique()) if not combined.empty else 0
    row["win_lift_pct"] = row["bias_strategy_d_win_rate_pct"] - row["strategy_d_win_rate_pct"]
    row["mean_lift_pct"] = row["bias_strategy_d_mean_return_pct"] - row["strategy_d_mean_return_pct"]
    row["median_lift_pct"] = row["bias_strategy_d_median_return_pct"] - row["strategy_d_median_return_pct"]
    row["effective_lift_pct"] = (
        row["bias_strategy_d_effective_up_rate_pct"] - row["strategy_d_effective_up_rate_pct"]
    )
    return row


def _prefixed_metrics(
    prefix: str,
    rows: pd.DataFrame,
    return_col: str,
    max_return_col: str,
    effective_threshold: float,
) -> dict[str, Any]:
    returns = rows[return_col].dropna()
    max_returns = rows[max_return_col].dropna()
    if returns.empty:
        return {
            f"{prefix}_events": 0,
            f"{prefix}_win_rate_pct": 0.0,
            f"{prefix}_effective_up_rate_pct": 0.0,
            f"{prefix}_touched_profit_rate_pct": 0.0,
            f"{prefix}_touched_effective_up_rate_pct": 0.0,
            f"{prefix}_mean_return_pct": 0.0,
            f"{prefix}_median_return_pct": 0.0,
            f"{prefix}_min_return_pct": 0.0,
            f"{prefix}_max_return_pct": 0.0,
            f"{prefix}_mean_max_return_pct": 0.0,
        }
    return {
        f"{prefix}_events": int(len(returns)),
        f"{prefix}_win_rate_pct": _round_pct((returns > 0).mean() * 100),
        f"{prefix}_effective_up_rate_pct": _round_pct((returns >= effective_threshold).mean() * 100),
        f"{prefix}_touched_profit_rate_pct": _round_pct((max_returns > 0).mean() * 100),
        f"{prefix}_touched_effective_up_rate_pct": _round_pct((max_returns >= effective_threshold).mean() * 100),
        f"{prefix}_mean_return_pct": _round_pct(returns.mean()),
        f"{prefix}_median_return_pct": _round_pct(returns.median()),
        f"{prefix}_min_return_pct": _round_pct(returns.min()),
        f"{prefix}_max_return_pct": _round_pct(returns.max()),
        f"{prefix}_mean_max_return_pct": _round_pct(max_returns.mean()),
    }


def optimize_candidates(dataset: pd.DataFrame, config: ValidationConfig) -> pd.DataFrame:
    rows = [
        evaluate_candidate(dataset, spec, split="train", train_cutoff=config.train_cutoff)
        for spec in iter_candidate_specs(config)
    ]
    candidates = pd.DataFrame(rows)
    if candidates.empty:
        return candidates
    candidates["passes_sample_filter"] = (
        (candidates["bias_strategy_d_events"] >= config.min_pattern_events)
        & (candidates["coverage_pct"] >= config.min_coverage_pct)
        & (candidates["ticker_count"] >= config.min_tickers)
    )
    candidates["score"] = (
        candidates["mean_lift_pct"]
        + candidates["win_lift_pct"] * 0.08
        + candidates["coverage_pct"] * 0.03
        + candidates["effective_lift_pct"] * 0.04
    )
    candidates = candidates.sort_values(
        ["passes_sample_filter", "score", "bias_strategy_d_events"],
        ascending=[False, False, False],
    )
    return candidates.reset_index(drop=True)


def select_best_primary_candidate(candidate_results: pd.DataFrame, config: ValidationConfig) -> CandidateSpec | None:
    if candidate_results.empty:
        return None

    keys = ["period", "threshold", "pre_days", "min_count"]
    primary = candidate_results[candidate_results["forward_days"].isin(config.primary_forward_days)]
    rows: list[dict[str, Any]] = []
    for values, group in primary.groupby(keys):
        if set(group["forward_days"]) != set(config.primary_forward_days):
            continue
        if not bool(group["passes_sample_filter"].all()):
            continue
        rows.append(
            {
                **dict(zip(keys, values)),
                "score": float(group["score"].mean()),
                "min_win_lift_pct": float(group["win_lift_pct"].min()),
                "min_mean_lift_pct": float(group["mean_lift_pct"].min()),
                "min_effective_lift_pct": float(group["effective_lift_pct"].min()),
                "min_coverage_pct": float(group["coverage_pct"].min()),
                "min_events": int(group["bias_strategy_d_events"].min()),
            }
        )
    if not rows:
        return None

    ranked = pd.DataFrame(rows).sort_values(
        ["score", "min_win_lift_pct", "min_mean_lift_pct", "min_events"],
        ascending=[False, False, False, False],
    )
    best = ranked.iloc[0]
    return CandidateSpec(
        period=int(best["period"]),
        threshold=float(best["threshold"]),
        pre_days=int(best["pre_days"]),
        min_count=int(best["min_count"]),
        forward_days=int(config.primary_forward_days[-1]),
    )


def evaluate_specs_across_splits(
    dataset: pd.DataFrame,
    specs: Iterable[CandidateSpec],
    config: ValidationConfig,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in specs:
        for split in ("train", "test", "all"):
            rows.append(evaluate_candidate(dataset, spec, split=split, train_cutoff=config.train_cutoff))
    return pd.DataFrame(rows)


def by_ticker_metrics(
    dataset: pd.DataFrame,
    spec: CandidateSpec,
    split: str,
    train_cutoff: str,
) -> pd.DataFrame:
    rows = []
    for ticker, ticker_df in dataset.groupby("ticker"):
        metrics = evaluate_candidate(ticker_df, spec, split=split, train_cutoff=train_cutoff)
        rows.append(
            {
                "ticker": ticker,
                "name": str(ticker_df["name"].iloc[0]),
                "years_loaded": int(ticker_df["years_loaded"].iloc[0]),
                "first_date": str(ticker_df["date"].iloc[0]),
                "last_date": str(ticker_df["date"].iloc[-1]),
                "rows": int(len(ticker_df)),
                "strategy_d_events": metrics["strategy_d_events"],
                "bias_strategy_d_events": metrics["bias_strategy_d_events"],
                "coverage_pct": metrics["coverage_pct"],
                "strategy_d_win_rate_pct": metrics["strategy_d_win_rate_pct"],
                "bias_strategy_d_win_rate_pct": metrics["bias_strategy_d_win_rate_pct"],
                "win_lift_pct": metrics["win_lift_pct"],
                "strategy_d_mean_return_pct": metrics["strategy_d_mean_return_pct"],
                "bias_strategy_d_mean_return_pct": metrics["bias_strategy_d_mean_return_pct"],
                "mean_lift_pct": metrics["mean_lift_pct"],
                "bias_only_events": metrics["bias_only_events"],
                "bias_only_win_rate_pct": metrics["bias_only_win_rate_pct"],
                "bias_only_mean_return_pct": metrics["bias_only_mean_return_pct"],
            }
        )
    return pd.DataFrame(rows).sort_values(["bias_strategy_d_events", "ticker"], ascending=[False, True])


def current_specs(config: ValidationConfig) -> list[CandidateSpec]:
    return [
        CandidateSpec(
            period=config.current_period,
            threshold=config.current_threshold,
            pre_days=config.current_pre_days,
            min_count=config.current_min_count,
            forward_days=days,
        )
        for days in config.forward_days
    ]


def spec_from_row(row: pd.Series | dict[str, Any]) -> CandidateSpec:
    return CandidateSpec(
        period=int(row["period"]),
        threshold=float(row["threshold"]),
        pre_days=int(row["pre_days"]),
        min_count=int(row["min_count"]),
        forward_days=int(row["forward_days"]),
    )


def verdict_for_selected(selected_metrics: pd.DataFrame, config: ValidationConfig) -> str:
    test = selected_metrics[selected_metrics["split"] == "test"]
    all_rows = selected_metrics[selected_metrics["split"] == "all"]
    primary_tests = [
        _first_row(test[test["forward_days"] == days])
        for days in config.primary_forward_days
    ]
    primary_tests = [row for row in primary_tests if row is not None]
    all_primary = [
        _first_row(all_rows[all_rows["forward_days"] == days])
        for days in config.primary_forward_days
    ]
    all_primary = [row for row in all_primary if row is not None]
    if not primary_tests:
        return "observe_only"

    passes_primary = all(
        row["bias_strategy_d_events"] >= config.min_pattern_events
        and row["coverage_pct"] >= config.min_coverage_pct
        and row["ticker_count"] >= config.min_tickers
        and row["win_lift_pct"] >= config.min_primary_win_lift_pct
        and row["mean_lift_pct"] >= config.min_primary_mean_lift_pct
        for row in primary_tests
    )
    secondary_rows = test[~test["forward_days"].isin(config.primary_forward_days)]
    passes_secondary = all(
        row["win_lift_pct"] >= -config.max_secondary_win_decline_pct
        and row["mean_lift_pct"] >= -config.max_secondary_mean_decline_pct
        for row in secondary_rows.to_dict("records")
    )
    if passes_primary and passes_secondary:
        return "implement"
    if all_primary and all(row["mean_lift_pct"] > 0 and row["win_lift_pct"] > 0 for row in all_primary):
        return "observe_only"
    return "do_not_implement"


def render_markdown_report(
    *,
    context: dict[str, Any],
    strategy_params: dict[str, Any],
    ticker_summary: pd.DataFrame,
    skipped: list[dict[str, Any]],
    current_metrics: pd.DataFrame,
    candidate_results: pd.DataFrame,
    selected_metrics: pd.DataFrame,
    selected_by_ticker: pd.DataFrame,
    selected_spec: CandidateSpec | None,
    verdict: str,
    config: ValidationConfig,
) -> str:
    lines: list[str] = []
    lines.append("# BIAS Before Strategy D Validation")
    lines.append("")
    lines.append("## Data")
    lines.append(f"- Watchlist source: `{context.get('source')}`")
    lines.append(f"- User id: `{context.get('user_id') or 'default'}`")
    lines.append(f"- Loaded tickers: {len(ticker_summary)}")
    lines.append(f"- Skipped tickers: {len(skipped)}")
    lines.append(f"- Strategy D buy events: {int(ticker_summary['strategy_d_buy_events'].sum()) if not ticker_summary.empty else 0}")
    lines.append(f"- Train/test cutoff: {config.train_cutoff}")
    lines.append("")
    lines.append("## Current Strategy D Buy Params")
    lines.append(_markdown_table(pd.DataFrame([strategy_d_buy_param_summary(strategy_params)])))
    lines.append("")
    lines.append("## Baseline Hypothesis")
    lines.append(
        f"Current BIAS gate: period={config.current_period}, threshold={config.current_threshold}, "
        f"prior_days={config.current_pre_days}, min_count={config.current_min_count}."
    )
    lines.append(_markdown_table(_display_metrics(current_metrics)))
    lines.append("")
    lines.append("## Optimized Candidate")
    if selected_spec is None:
        lines.append("No candidate passed the sample filter.")
    else:
        lines.append(
            f"Selected: period={selected_spec.period}, threshold={selected_spec.threshold}, "
            f"prior_days={selected_spec.pre_days}, min_count={selected_spec.min_count}, "
            f"forward_days={selected_spec.forward_days}."
        )
        lines.append(f"Verdict: `{verdict}`")
        lines.append(_markdown_table(_display_metrics(selected_metrics)))
    lines.append("")
    lines.append("## Top Candidates")
    top_cols = [
        "period",
        "threshold",
        "pre_days",
        "min_count",
        "forward_days",
        "bias_strategy_d_events",
        "coverage_pct",
        "ticker_count",
        "win_lift_pct",
        "mean_lift_pct",
        "effective_lift_pct",
        "score",
        "passes_sample_filter",
    ]
    lines.append(_markdown_table(candidate_results.head(20)[top_cols]))
    lines.append("")
    lines.append("## Selected Candidate By Ticker")
    if selected_by_ticker.empty:
        lines.append("No selected candidate.")
    else:
        lines.append(_markdown_table(selected_by_ticker))
    lines.append("")
    if skipped:
        lines.append("## Skipped")
        lines.append(_markdown_table(pd.DataFrame(skipped)))
        lines.append("")
    lines.append("## Decision Standard")
    primary = "/".join(f"{days}d" for days in config.primary_forward_days)
    lines.append(f"- Primary endpoint standard: {primary} close-to-close return must improve.")
    lines.append(f"- Implement if each primary test sample count >= {config.min_pattern_events}.")
    lines.append(f"- Implement if each primary test coverage >= {config.min_coverage_pct}%.")
    lines.append(f"- Implement if each primary test ticker count >= {config.min_tickers}.")
    lines.append(f"- Implement if each primary test win lift >= {config.min_primary_win_lift_pct} percentage points.")
    lines.append(f"- Implement if each primary test mean return lift >= {config.min_primary_mean_lift_pct}%.")
    lines.append("- The touched-profit metrics are diagnostic only because they are intentionally looser.")
    lines.append("- Do not implement if optimized result is weaker than plain Strategy D or only works in-sample.")
    lines.append("")
    return "\n".join(lines)


def _display_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "split",
        "period",
        "threshold",
        "pre_days",
        "min_count",
        "forward_days",
        "strategy_d_events",
        "bias_strategy_d_events",
        "coverage_pct",
        "ticker_count",
        "strategy_d_win_rate_pct",
        "bias_strategy_d_win_rate_pct",
        "win_lift_pct",
        "strategy_d_mean_return_pct",
        "bias_strategy_d_mean_return_pct",
        "mean_lift_pct",
        "strategy_d_effective_up_rate_pct",
        "bias_strategy_d_effective_up_rate_pct",
        "effective_lift_pct",
        "strategy_d_touched_profit_rate_pct",
        "bias_strategy_d_touched_profit_rate_pct",
        "strategy_d_mean_max_return_pct",
        "bias_strategy_d_mean_max_return_pct",
        "bias_only_events",
        "bias_only_win_rate_pct",
        "bias_only_mean_return_pct",
        "all_non_signal_win_rate_pct",
        "all_non_signal_mean_return_pct",
    ]
    return metrics[[col for col in cols if col in metrics]].copy()


def write_outputs(
    output_dir: Path,
    report_markdown: str,
    ticker_summary: pd.DataFrame,
    current_metrics: pd.DataFrame,
    candidate_results: pd.DataFrame,
    selected_metrics: pd.DataFrame,
    selected_by_ticker: pd.DataFrame,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report": output_dir / "report.md",
        "ticker_summary": output_dir / "ticker_summary.csv",
        "current_metrics": output_dir / "current_metrics.csv",
        "candidate_results": output_dir / "candidate_results.csv",
        "selected_metrics": output_dir / "selected_metrics.csv",
        "selected_by_ticker": output_dir / "selected_by_ticker.csv",
    }
    paths["report"].write_text(report_markdown, encoding="utf-8")
    ticker_summary.to_csv(paths["ticker_summary"], index=False)
    current_metrics.to_csv(paths["current_metrics"], index=False)
    candidate_results.to_csv(paths["candidate_results"], index=False)
    selected_metrics.to_csv(paths["selected_metrics"], index=False)
    selected_by_ticker.to_csv(paths["selected_by_ticker"], index=False)
    return paths


def _first_row(df: pd.DataFrame) -> dict[str, Any] | None:
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def _safe_pct(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return _round_pct(part / whole * 100)


def _round_pct(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return round(float(value), 2)


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    display = df.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda value: f"{float(value):.2f}")
    headers = [str(col) for col in display.columns]
    rows = [
        [_markdown_cell(value) for value in row]
        for row in display.astype(object).itertuples(index=False, name=None)
    ]
    header_line = "| " + " | ".join(_markdown_cell(header) for header in headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"
    row_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator_line, *row_lines])


def _markdown_cell(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")
