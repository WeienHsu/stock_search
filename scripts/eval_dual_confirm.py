"""Evaluate the "dual-confirmation" entry: an original (confirmed) Strategy D
signal and an early (MACD-divergence) signal of the SAME direction firing within
W trading days of each other.

Question: if you act on that co-occurrence, is the forward win rate high?

Method
------
* Pairing: for one direction (buy or sell), a dual-confirm entry exists whenever a
  confirmed signal index c and an early signal index e satisfy |c - e| <= W.
* Entry day T = max(c, e) — you only know both fired once the later one appears,
  so entering before T would use future information.
* Entry price = close[T] (the close that confirms the signal; causal).
* Dedup: keep non-overlapping entries (skip any within DEDUP_GAP bars of the last
  kept one) so a single market move isn't counted as several trades.
* Settlement: for each horizon h, return = (close[T+h] - close[T]) / close[T] for
  buy, negated for sell (a sell "wins" when price falls). A trade wins if its
  return > 0. Entries without a full h-bar future are dropped at that horizon.

A win rate alone is meaningless (in a bull run anything is >50%), so the report
also shows three baselines per horizon/direction:
  * unconditional — every bar's forward return (the "buy a random day" base rate)
  * confirmed-only — all confirmed entries, deduped
  * early-only     — all early entries, deduped
The edge (dual win rate minus unconditional) is what tells you it's "high".

Usage: .venv/bin/python scripts/eval_dual_confirm.py
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.repositories.watchlist_repo import _default_watchlist
from src.strategies.strategy_d import StrategyD

HORIZONS = [1, 3, 5, 10, 20]   # settlement points, in trading days after entry
MAX_HORIZON = max(HORIZONS)
DEFAULT_W = 3                  # co-occurrence window (the "三日內" the question asks)
WINDOWS = [1, 2, 3, 5]         # sensitivity sweep for W
DEDUP_GAP = MAX_HORIZON        # non-overlap spacing between counted entries
YEARS = 5                      # more history -> more (rare) dual-confirm samples

TW_EXTRA = ["0050.TW", "3037.TW", "2382.TW", "6491.TW", "3081.TWO"]


def universe() -> list[str]:
    us = [
        i["ticker"]
        for i in _default_watchlist()
        if not str(i["ticker"]).upper().endswith((".TW", ".TWO"))
    ]
    return us + TW_EXTRA


@dataclass
class TickerData:
    ticker: str
    close: list[float]
    last: int
    conf: dict[str, list[int]]   # "buy"/"sell" -> confirmed entry bar indices
    early: dict[str, list[int]]  # "buy"/"sell" -> early entry bar indices


def _non_overlap(idxs: set[int], gap: int) -> list[int]:
    kept: list[int] = []
    last_kept = -(gap + 1)
    for i in sorted(idxs):
        if i - last_kept > gap:
            kept.append(i)
            last_kept = i
    return kept


def _dual_entries(conf: list[int], early: list[int], w: int) -> set[int]:
    """Entry bars where a confirmed and an early signal fire within w bars."""
    entries: set[int] = set()
    early_sorted = sorted(early)
    for c in conf:
        for e in early_sorted:
            if abs(c - e) <= w:
                entries.add(max(c, e))
    return entries


def _returns(close: list[float], entries: list[int], side: str, last: int) -> dict[int, list[float]]:
    out: dict[int, list[float]] = {h: [] for h in HORIZONS}
    for t in entries:
        base = close[t]
        if base <= 0:
            continue
        for h in HORIZONS:
            if t + h <= last:
                r = (close[t + h] - base) / base
                out[h].append(-r if side == "sell" else r)
    return out


def _merge(dst: dict[int, list[float]], src: dict[int, list[float]]) -> None:
    for h in HORIZONS:
        dst[h].extend(src[h])


def _baseline(close: list[float], last: int, side: str) -> dict[int, list[float]]:
    """Forward return from every bar — the unconditional base rate."""
    out: dict[int, list[float]] = {h: [] for h in HORIZONS}
    for t in range(0, last + 1):
        base = close[t]
        if base <= 0:
            continue
        for h in HORIZONS:
            if t + h <= last:
                r = (close[t + h] - base) / base
                out[h].append(-r if side == "sell" else r)
    return out


def _stats(rets: list[float]) -> tuple[int, float, float, float]:
    n = len(rets)
    if n == 0:
        return 0, float("nan"), float("nan"), float("nan")
    wr = sum(1 for r in rets if r > 0) / n
    return n, wr, statistics.mean(rets), statistics.median(rets)


def _print_block(title: str, by_h: dict[int, list[float]], base: dict[int, list[float]]) -> None:
    print(f"\n  {title}")
    print(f"    {'h(td)':>6}{'n':>6}{'win%':>8}{'mean%':>9}{'median%':>10}{'base win%':>11}{'edge':>8}")
    for h in HORIZONS:
        n, wr, mean, med = _stats(by_h[h])
        _, bwr, _, _ = _stats(base[h])
        if n == 0:
            print(f"    {h:>6}{n:>6}{'—':>8}{'—':>9}{'—':>10}{bwr * 100:>10.1f}%{'—':>8}")
            continue
        edge = (wr - bwr) * 100
        print(f"    {h:>6}{n:>6}{wr * 100:>7.1f}%{mean * 100:>8.2f}%{med * 100:>9.2f}%"
              f"{bwr * 100:>10.1f}%{edge:>+7.1f}")


def main() -> None:
    strat = StrategyD()
    params = {**strat.default_params(), "enable_early_signal": True}

    data: list[TickerData] = []
    skipped: list[str] = []

    for tk in universe():
        try:
            df = fetch_prices_for_strategy(tk, years=YEARS)
        except Exception as exc:  # noqa: BLE001
            skipped.append(f"{tk}: fetch error {exc}")
            continue
        if df.empty or len(df) < 60:
            skipped.append(f"{tk}: insufficient data ({0 if df.empty else len(df)} bars)")
            continue

        df = df.reset_index(drop=True)
        sigs = strat.compute(df, params)
        date_to_idx = {str(d)[:10]: i for i, d in enumerate(df["date"].reset_index(drop=True))}
        close = [float(c) for c in df["close"].reset_index(drop=True)]

        conf = {"buy": [], "sell": []}
        early = {"buy": [], "sell": []}
        for s in sigs:
            if s.signal_type not in ("buy", "sell"):
                continue
            idx = date_to_idx.get(s.date)
            if idx is None:
                continue
            (early if s.tier == "early" else conf)[s.signal_type].append(idx)

        data.append(TickerData(tk, close, len(close) - 1, conf, early))

    print(f"\nUniverse: {len(data)} tickers evaluated, {len(skipped)} skipped")
    print(f"Params: W(default)={DEFAULT_W} td, horizons={HORIZONS} td, "
          f"dedup_gap={DEDUP_GAP} td, YEARS={YEARS}")
    print("Win = forward return > 0.  Entry = close of co-occurrence day T = max(confirmed, early).")

    for side in ("buy", "sell"):
        print(f"\n{'=' * 64}\n {side.upper()} side\n{'=' * 64}")

        dual: dict[int, list[float]] = {h: [] for h in HORIZONS}
        conf_only: dict[int, list[float]] = {h: [] for h in HORIZONS}
        early_only: dict[int, list[float]] = {h: [] for h in HORIZONS}
        base: dict[int, list[float]] = {h: [] for h in HORIZONS}
        n_dual_trades = 0
        contributing = 0

        for d in data:
            entries = _non_overlap(_dual_entries(d.conf[side], d.early[side], DEFAULT_W), DEDUP_GAP)
            if entries:
                contributing += 1
                n_dual_trades += len(entries)
            _merge(dual, _returns(d.close, entries, side, d.last))
            _merge(conf_only, _returns(d.close, _non_overlap(set(d.conf[side]), DEDUP_GAP), side, d.last))
            _merge(early_only, _returns(d.close, _non_overlap(set(d.early[side]), DEDUP_GAP), side, d.last))
            _merge(base, _baseline(d.close, d.last, side))

        print(f"\n  dual-confirm entries: {n_dual_trades} trades across {contributing} tickers")
        _print_block(f"DUAL-CONFIRM (confirmed + early within {DEFAULT_W} td)", dual, base)
        _print_block("confirmed-only", conf_only, base)
        _print_block("early-only", early_only, base)

        # ── window sensitivity: dual-confirm win rate vs W ──
        print(f"\n  W sensitivity (dual-confirm win% at selected horizons)")
        print(f"    {'W':>3}{'trades':>8}{'win@5':>9}{'win@10':>9}{'win@20':>9}")
        for w in WINDOWS:
            sweep: dict[int, list[float]] = {h: [] for h in HORIZONS}
            trades = 0
            for d in data:
                entries = _non_overlap(_dual_entries(d.conf[side], d.early[side], w), DEDUP_GAP)
                trades += len(entries)
                _merge(sweep, _returns(d.close, entries, side, d.last))

            def wr(h: int) -> str:
                n, w_, _, _ = _stats(sweep[h])
                return f"{w_ * 100:.1f}%" if n else "—"

            print(f"    {w:>3}{trades:>8}{wr(5):>9}{wr(10):>9}{wr(20):>9}")

    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  {s}")


if __name__ == "__main__":
    main()
