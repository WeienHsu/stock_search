"""Evaluate Strategy D early (MACD-divergence) signals against swing reversals.

Ground truth: swing reversal points where a bar's low/high is the extreme of a
+/- ORDER trading-day window. An early signal "hits" a reversal when it falls in
[reversal - LEAD_MAX, reversal + LATE_MAX] trading days.

Metrics per ticker and aggregated:
  recall    — share of reversal points hit by >=1 early signal
  precision — share of early signals that land in some reversal window
  lead      — (reversal_idx - signal_idx) in trading days for matched signals
Also reports lead-vs-confirmed (how many trading days early vs the confirmed
Strategy D signal) as the practically meaningful timeliness measure.

Usage: .venv/bin/python scripts/eval_early_signal.py
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.repositories.watchlist_repo import _default_watchlist
from src.strategies.strategy_d import (
    StrategyD,
    _swing_high_indices,
    _swing_low_indices,
    prepare_df,
    scan_divergence_buy,
    scan_divergence_sell,
)

ORDER = 3          # swing window: +/- 3 trading days (ground truth)
MAJOR_ORDER = 10   # context: recall against major swings only
LEAD_MAX = 5       # signal may lead reversal by at most 5 trading days
LATE_MAX = 2       # signal may lag reversal by at most 2 trading days
YEARS = 3

TW_EXTRA = ["0050.TW", "3037.TW", "2382.TW", "6491.TW", "3081.TWO"]

# Success thresholds (from the goal)
T_RECALL = 0.90
T_PRECISION = 0.80
T_MEAN_LEAD = 2.0
T_MAX_LEAD = 5.0


def universe() -> list[str]:
    us = [
        i["ticker"]
        for i in _default_watchlist()
        if not str(i["ticker"]).upper().endswith((".TW", ".TWO"))
    ]
    return us + TW_EXTRA


@dataclass
class SideResult:
    side: str
    n_reversals: int
    n_signals: int
    hits: int          # reversals hit
    matched: int       # signals that matched
    leads: list[int]


def _eval_side(
    df: pd.DataFrame,
    reversal_idxs: list[int],
    signal_idxs: list[int],
    side: str,
) -> SideResult:
    rev_set = set(reversal_idxs)
    hit_revs = set()
    matched = 0
    leads: list[int] = []
    for s in signal_idxs:
        # reversal allowed in [s - LATE_MAX, s + LEAD_MAX]
        cands = [r for r in rev_set if s - LATE_MAX <= r <= s + LEAD_MAX]
        if cands:
            matched += 1
            nearest = min(cands, key=lambda r: abs(r - s))
            hit_revs.add(nearest)
            leads.append(nearest - s)  # >0 = signal before reversal
    return SideResult(side, len(reversal_idxs), len(signal_idxs), len(hit_revs), matched, leads)


def _confirmed_lead(df: pd.DataFrame, early: list, confirmed: list) -> list[int]:
    """For each early signal, trading days earlier than the next confirmed signal
    of the same type within 20 bars (negative if early is later)."""
    date_to_idx = {str(d)[:10]: i for i, d in enumerate(df["date"].reset_index(drop=True))}
    out: list[int] = []
    for e in early:
        ei = date_to_idx.get(e.date)
        if ei is None:
            continue
        future = [
            date_to_idx[c.date] - ei
            for c in confirmed
            if c.signal_type == e.signal_type and c.date in date_to_idx
            and 0 <= date_to_idx[c.date] - ei <= 20
        ]
        if future:
            out.append(min(future))
    return out


def main() -> None:
    strat = StrategyD()
    params = {**strat.default_params(), "enable_early_signal": True}

    agg = {
        "buy": SideResult("buy", 0, 0, 0, 0, []),
        "sell": SideResult("sell", 0, 0, 0, 0, []),
    }
    conf_leads: list[int] = []
    per_ticker: list[dict] = []
    skipped: list[str] = []
    major = {"buy_rev": 0, "buy_hit": 0, "sell_rev": 0, "sell_hit": 0}
    # Cache prepared data per ticker for the precision-recall sweep below.
    cache: list[dict] = []

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
        ind = prepare_df(df, params)
        low = ind["low"].reset_index(drop=True)
        high = ind["high"].reset_index(drop=True)
        swing_lows = _swing_low_indices(low, ORDER)
        swing_highs = _swing_high_indices(high, ORDER)

        sigs = strat.compute(df, params)
        early = [s for s in sigs if s.tier == "early"]
        confirmed = [s for s in sigs if s.tier == "confirmed"]
        date_to_idx = {str(d)[:10]: i for i, d in enumerate(ind["date"].reset_index(drop=True))}
        buy_sig_idx = [date_to_idx[s.date] for s in early if s.signal_type == "buy" and s.date in date_to_idx]
        sell_sig_idx = [date_to_idx[s.date] for s in early if s.signal_type == "sell" and s.date in date_to_idx]

        rb = _eval_side(ind, swing_lows, buy_sig_idx, "buy")
        rs = _eval_side(ind, swing_highs, sell_sig_idx, "sell")
        cl = _confirmed_lead(ind, early, confirmed)
        conf_leads.extend(cl)

        cache.append({
            "ind": ind, "date_to_idx": date_to_idx,
            "swing_lows": swing_lows, "swing_highs": swing_highs,
        })

        maj_lows = _swing_low_indices(low, MAJOR_ORDER)
        maj_highs = _swing_high_indices(high, MAJOR_ORDER)
        mb = _eval_side(ind, maj_lows, buy_sig_idx, "buy")
        ms = _eval_side(ind, maj_highs, sell_sig_idx, "sell")
        major["buy_rev"] += mb.n_reversals
        major["buy_hit"] += mb.hits
        major["sell_rev"] += ms.n_reversals
        major["sell_hit"] += ms.hits

        for r in (rb, rs):
            a = agg[r.side]
            a.n_reversals += r.n_reversals
            a.n_signals += r.n_signals
            a.hits += r.hits
            a.matched += r.matched
            a.leads.extend(r.leads)

        n_sig = rb.n_signals + rs.n_signals
        n_match = rb.matched + rs.matched
        prec = n_match / n_sig if n_sig else float("nan")
        leads_all = rb.leads + rs.leads
        per_ticker.append({
            "ticker": tk,
            "bars": len(df),
            "early": n_sig,
            "matched": n_match,
            "precision": prec,
            "mean_lead": statistics.mean(leads_all) if leads_all else float("nan"),
            "max_lead": max(leads_all) if leads_all else float("nan"),
        })

    # ── report ────────────────────────────────────────────────────────────────
    print(f"\nUniverse: {len(per_ticker)} tickers evaluated, {len(skipped)} skipped")
    print(f"Params: ORDER={ORDER}, window=[-{LEAD_MAX},+{LATE_MAX}] trading days, YEARS={YEARS}\n")
    print(f"{'ticker':<10}{'bars':>6}{'early':>7}{'matched':>9}{'prec':>7}{'meanLd':>8}{'maxLd':>7}")
    for r in per_ticker:
        print(f"{r['ticker']:<10}{r['bars']:>6}{r['early']:>7}{r['matched']:>9}"
              f"{r['precision']:>7.2f}{r['mean_lead']:>8.2f}{r['max_lead']:>7.0f}")

    print("\n── Aggregate ─────────────────────────────")
    for side in ("buy", "sell"):
        a = agg[side]
        recall = a.hits / a.n_reversals if a.n_reversals else float("nan")
        prec = a.matched / a.n_signals if a.n_signals else float("nan")
        ml = statistics.mean(a.leads) if a.leads else float("nan")
        xl = max(a.leads) if a.leads else float("nan")
        print(f"{side:>4}: reversals={a.n_reversals:>4} signals={a.n_signals:>4} "
              f"hits={a.hits:>4} recall={recall:.2f} precision={prec:.2f} "
              f"mean_lead={ml:.2f} max_lead={xl}")

    all_leads = agg["buy"].leads + agg["sell"].leads
    n_sig = agg["buy"].n_signals + agg["sell"].n_signals
    n_match = agg["buy"].matched + agg["sell"].matched
    n_rev = agg["buy"].n_reversals + agg["sell"].n_reversals
    n_hit = agg["buy"].hits + agg["sell"].hits
    overall_recall = n_hit / n_rev if n_rev else float("nan")
    overall_prec = n_match / n_sig if n_sig else float("nan")
    overall_mean_lead = statistics.mean(all_leads) if all_leads else float("nan")
    overall_max_lead = max(all_leads) if all_leads else float("nan")

    print("\n── Overall ───────────────────────────────")
    print(f"recall    = {overall_recall:.3f}  (target >= {T_RECALL})")
    print(f"precision = {overall_prec:.3f}  (target >= {T_PRECISION})")
    print(f"mean_lead = {overall_mean_lead:.2f} td  (target >= {T_MEAN_LEAD})")
    print(f"max_lead  = {overall_max_lead} td  (target <= {T_MAX_LEAD})")
    if conf_leads:
        print(f"lead vs confirmed: mean={statistics.mean(conf_leads):.2f} td, "
              f"median={statistics.median(conf_leads)} td, n={len(conf_leads)}")

    maj_rev = major["buy_rev"] + major["sell_rev"]
    maj_hit = major["buy_hit"] + major["sell_hit"]
    if maj_rev:
        print(f"recall vs MAJOR swings (order={MAJOR_ORDER}) = "
              f"{maj_hit / maj_rev:.3f}  ({maj_hit}/{maj_rev})")

    print("\n── Per-ticker pass (precision>=0.8 & has signals) ──")
    passed = [r for r in per_ticker if r["early"] and r["precision"] >= T_PRECISION]
    print(f"{len(passed)}/{len(per_ticker)} tickers pass precision>=0.8")
    fails = [r for r in per_ticker if not (r["early"] and r["precision"] >= T_PRECISION)]
    for r in fails:
        why = "no early signals" if not r["early"] else f"precision={r['precision']:.2f}"
        print(f"  FAIL {r['ticker']}: {why}")
    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  {s}")

    # ── precision-recall tradeoff curve (stop-loss #2) ─────────────────────────
    # Selectivity knob = early_pivot_order: smaller -> more signals (looser),
    # larger -> fewer, only-major-swing signals (stricter). Ground-truth swings
    # stay at ORDER=3. This is the curve to pick a threshold against.
    print("\n── Precision-Recall tradeoff (vary early_pivot_order) ──")
    print(f"{'pivot':>6}{'signals':>9}{'recall':>8}{'precision':>11}{'mean_lead':>11}")
    for po in (1, 2, 3, 4, 5):
        s_tot = m_tot = r_tot = h_tot = 0
        leads: list[int] = []
        for c in cache:
            ind = c["ind"]
            d2i = c["date_to_idx"]
            db = scan_divergence_buy(ind, po, 3, 40)
            ds = scan_divergence_sell(ind, po, 3, 40)
            bidx = [d2i[d] for d in db["date"].astype(str).str[:10] if d in d2i] if not db.empty else []
            sidx = [d2i[d] for d in ds["date"].astype(str).str[:10] if d in d2i] if not ds.empty else []
            rb = _eval_side(ind, c["swing_lows"], bidx, "buy")
            rs = _eval_side(ind, c["swing_highs"], sidx, "sell")
            s_tot += rb.n_signals + rs.n_signals
            m_tot += rb.matched + rs.matched
            r_tot += rb.n_reversals + rs.n_reversals
            h_tot += rb.hits + rs.hits
            leads.extend(rb.leads + rs.leads)
        rec = h_tot / r_tot if r_tot else float("nan")
        prec = m_tot / s_tot if s_tot else float("nan")
        ml = statistics.mean(leads) if leads else float("nan")
        print(f"{po:>6}{s_tot:>9}{rec:>8.3f}{prec:>11.3f}{ml:>11.2f}")


if __name__ == "__main__":
    main()
