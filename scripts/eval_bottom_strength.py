"""P1 — bottom-strength scoring (docs/research_20260630.md).

Limitation #2 from the turning-point study: the indicator finds bottoms but can't
tell which bottom precedes a big rally (+3/+5/+10% tiers had near-identical recall).
This script tests whether a per-signal STRENGTH SCORE separates good bottoms from
weak ones — exactly the input a long-term holder needs to decide where to add more.

For every buy signal (union = confirmed + early), four causal factors are measured
at the signal bar (only data up to that bar), each oriented so higher = stronger
bottom candidate:
  kd_oversold   = -K            (deeper KD oversold)
  bias_below    = -bias_20      (further below MA20)
  vol_spike     = vol / 20d avg (capitulation volume)
  hist_recovery = 1 - |hist|/|recent trough|  (MACD histogram convergence)

Each factor is percentile-ranked across all signals; the composite is their mean.
Signals are bucketed into low/mid/high thirds by each factor and by the composite,
and forward returns at 10/20/40/60 td are compared. If high-score bottoms beat
low-score bottoms, the score works.

Note: percentile ranking uses the whole sample (a research-time relative ranking,
not a live trading rule); factors themselves are strictly causal.

Usage: PYTHONPATH=. .venv/bin/python scripts/eval_bottom_strength.py
"""
from __future__ import annotations

import statistics

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.indicators.bias import add_bias
from src.indicators.ma import add_ma
from src.repositories.watchlist_repo import _default_watchlist
from src.strategies.strategy_d import StrategyD, prepare_df

HORIZONS = [10, 20, 40, 60]      # forward settlement points (trading days)
DEDUP_GAP = 5                    # collapse signals within this many bars to one bottom
HIST_LOOKBACK = 20               # bars to find the histogram trough
YEARS = 5
FACTORS = ["kd_oversold", "bias_below", "bias60_below", "vol_spike", "hist_recovery"]

# Composite = weighted mean of percentile-ranked factors. Set a weight to 0 to drop
# a factor from the composite (it still gets its own per-factor analysis).
# /goal optimization (2026-06-30): bias_below (distance below MA20) alone gives the
# best long-horizon separation (h60 +8.4%); every combination diluted it, so the
# composite is just bias_below. See docs/research_20260630.md "P1" for the search log.
FACTOR_WEIGHTS = {
    "kd_oversold": 0.0,
    "bias_below": 1.0,
    "bias60_below": 0.0,
    "vol_spike": 0.0,
    "hist_recovery": 0.0,
}

TW_EXTRA = ["0050.TW", "3037.TW", "2382.TW", "6491.TW", "3081.TWO"]


def universe() -> list[str]:
    us = [
        i["ticker"]
        for i in _default_watchlist()
        if not str(i["ticker"]).upper().endswith((".TW", ".TWO"))
    ]
    return us + TW_EXTRA


def _non_overlap(idxs: set[int], gap: int) -> list[int]:
    kept: list[int] = []
    last = -(gap + 1)
    for i in sorted(idxs):
        if i - last > gap:
            kept.append(i)
            last = i
    return kept


def _factors_at(ind: pd.DataFrame, i: int) -> dict[str, float] | None:
    """Causal factors at bar i, oriented so higher = stronger bottom. None if NaN."""
    k = ind["K"].iloc[i]
    bias = ind["bias_20"].iloc[i]
    bias60 = ind["bias_60"].iloc[i]
    vol = ind["volume"].iloc[i]
    vol_avg = ind["volume"].iloc[max(0, i - 19): i + 1].mean()
    hist = ind["histogram"].iloc[i]
    lb = ind["histogram"].iloc[max(0, i - HIST_LOOKBACK + 1): i + 1]
    neg = lb[lb < 0]
    if (pd.isna(k) or pd.isna(bias) or pd.isna(bias60) or pd.isna(hist)
            or pd.isna(vol) or vol_avg <= 0 or neg.empty):
        return None
    trough = neg.min()
    return {
        "kd_oversold": -float(k),
        "bias_below": -float(bias),
        "bias60_below": -float(bias60),
        "vol_spike": float(vol) / float(vol_avg),
        "hist_recovery": 1.0 - abs(float(hist)) / abs(float(trough)) if trough != 0 else 0.0,
    }


def _pct_rank(vals: list[float]) -> list[float]:
    n = len(vals)
    if n <= 1:
        return [0.5] * n
    order = sorted(range(n), key=lambda i: vals[i])
    ranks = [0.0] * n
    for pos, idx in enumerate(order):
        ranks[idx] = pos / (n - 1)
    return ranks


def _buckets(records: list[dict], key: str) -> list[tuple[str, list[dict]]]:
    ordered = sorted(records, key=lambda r: r[key])
    n = len(ordered)
    a, b = n // 3, 2 * n // 3
    return [("low", ordered[:a]), ("mid", ordered[a:b]), ("high", ordered[b:])]


def _ret_stats(recs: list[dict], h: int) -> tuple[int, float, float, float]:
    rets = [r["ret"][h] for r in recs if h in r["ret"]]
    n = len(rets)
    if n == 0:
        return 0, float("nan"), float("nan"), float("nan")
    wr = sum(1 for x in rets if x > 0) / n
    return n, statistics.mean(rets), statistics.median(rets), wr


def main() -> None:
    strat = StrategyD()
    params = {**strat.default_params(), "enable_early_signal": True}

    records: list[dict] = []
    skipped: list[str] = []
    n_tickers = 0

    for tk in universe():
        try:
            df = fetch_prices_for_strategy(tk, years=YEARS)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{tk}: fetch error {exc}")
            continue
        if df.empty or len(df) < 120:
            skipped.append(f"{tk}: insufficient data ({0 if df.empty else len(df)} bars)")
            continue

        df = df.reset_index(drop=True)
        n_tickers += 1
        sigs = strat.compute(df, params)
        ind = prepare_df(df.copy(), params)
        ind = add_ma(ind, periods=[20, 60])
        ind = add_bias(ind, period=20)
        ind = add_bias(ind, period=60)
        ind = ind.reset_index(drop=True)

        date_to_idx = {str(d)[:10]: i for i, d in enumerate(ind["date"].reset_index(drop=True))}
        close = [float(c) for c in ind["close"].reset_index(drop=True)]
        last = len(close) - 1

        buys = {date_to_idx[s.date] for s in sigs
                if s.signal_type == "buy" and s.date in date_to_idx}
        for i in _non_overlap(buys, DEDUP_GAP):
            f = _factors_at(ind, i)
            if f is None:
                continue
            ret = {h: (close[i + h] - close[i]) / close[i] for h in HORIZONS if i + h <= last}
            if not ret:
                continue
            f["ret"] = ret
            records.append(f)

    # composite = weighted mean of percentile-ranked factors (FACTOR_WEIGHTS)
    for fac in FACTORS:
        ranks = _pct_rank([r[fac] for r in records])
        for r, rk in zip(records, ranks):
            r[f"_rank_{fac}"] = rk
    active = {f: w for f, w in FACTOR_WEIGHTS.items() if w and f in FACTORS}
    wsum = sum(active.values())
    for r in records:
        r["composite"] = (
            sum(w * r[f"_rank_{f}"] for f, w in active.items()) / wsum if wsum else 0.0
        )

    print(f"\nUniverse: {n_tickers} tickers, {len(skipped)} skipped")
    print(f"Buy signals scored: {len(records)} | horizons={HORIZONS} td | YEARS={YEARS}")
    print(f"Composite weights: {{{', '.join(f'{f}={w:g}' for f, w in active.items())}}}")
    print("If high-score bottoms beat low-score, the factor predicts. mean/win shown per horizon.\n")

    # overall baseline (all scored signals)
    print("  baseline — all scored buy signals")
    print(f"    {'h(td)':>6}{'n':>6}{'mean%':>9}{'median%':>10}{'win%':>8}")
    for h in HORIZONS:
        n, mean, med, wr = _ret_stats(records, h)
        print(f"    {h:>6}{n:>6}{mean * 100:>8.2f}%{med * 100:>9.2f}%{wr * 100:>7.0f}%")

    for key in FACTORS + ["composite"]:
        print(f"\n  by {key} (low/mid/high third)")
        print(f"    {'bucket':<7}{'h(td)':>6}{'n':>6}{'mean%':>9}{'median%':>10}{'win%':>8}")
        means: dict[str, dict[int, float]] = {}
        for bname, recs in _buckets(records, key):
            means[bname] = {}
            for h in HORIZONS:
                n, mean, med, wr = _ret_stats(recs, h)
                means[bname][h] = mean
                print(f"    {bname:<7}{h:>6}{n:>6}{mean * 100:>8.2f}%{med * 100:>9.2f}%{wr * 100:>7.0f}%")
        # high-minus-low spread per horizon (the signal that the factor separates)
        spread = "  ".join(
            f"h{h}:{(means['high'][h] - means['low'][h]) * 100:+.2f}%"
            for h in HORIZONS
            if means.get('high', {}).get(h) == means['high'].get(h) and means['high'].get(h) is not None
        )
        print(f"    high-low spread: {spread}")

    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  {s}")


if __name__ == "__main__":
    main()
