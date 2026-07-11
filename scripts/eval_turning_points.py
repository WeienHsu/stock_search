"""Evaluate how well Strategy D signals pinpoint real turning points, for a
long-term holder who wants to enter near a bottom (and optionally trim near a top)
rather than trade in and out.

Ground truth
------------
Turning points = swing lows/highs: a bar whose low/high is the extreme of a
+/- ORDER trading-day window and strictly beyond both neighbours. Larger ORDER =
bigger, more meaningful swings. Identified with full data (a benchmark, allowed to
be non-causal); the signals themselves stay causal.

Magnitude tiers (a "real" bottom should be followed by a real rally): a bottom is
counted in the +X% tier if the max close within the next RALLY_WINDOW trading days
rises >= X above the bottom close. Tops are symmetric (drop >= X). The "all" tier
keeps every swing point.

Metrics (bottom-/top-centric — does the indicator find the turn, and how close?)
  recall   — share of turning points with >=1 signal within +/- ORDER td
  med_pen  — median price penalty: how far above the bottom you bought (or below
             the top you sold), in %. The practical cost of imperfect timing.
  med_gap  — median signed distance signal-idx - turn-idx (td). Negative = signal
             fires before the turn (still falling/rising); positive = after.

Compared across three signal groups: confirmed-only, early-only, and their union,
so you can see whether the early layer catches more turns or buys closer to them.

Usage: PYTHONPATH=. .venv/bin/python scripts/eval_turning_points.py
"""
from __future__ import annotations

import statistics

import pandas as pd

from src.data.price_fetcher import fetch_prices_for_strategy
from src.repositories.watchlist_repo import _default_watchlist
from src.strategies.strategy_d import StrategyD, _swing_high_indices, _swing_low_indices

ORDERS = [10, 20]                              # swing scales (trading days)
MATCH_WINDOWS = [3, 5, 7, 10]                  # how close a signal must be to "catch" a turn
NEW_TURN_ORDER = 20                            # turn scale for the directional / both analysis
DIRECTIONS = ["sym", "before"]                 # sym = +/-W ; before = signal in [turn-W, turn]
TIERS = [("all", 0.0), ("+3%", 0.03), ("+5%", 0.05), ("+10%", 0.10)]
RALLY_WINDOW = 60                              # forward window to measure the move
MIN_FWD = 20                                   # need this many forward bars to classify magnitude
YEARS = 5

TW_EXTRA = ["0050.TW", "3037.TW", "2382.TW", "6491.TW", "3081.TWO"]


def universe() -> list[str]:
    us = [
        i["ticker"]
        for i in _default_watchlist()
        if not str(i["ticker"]).upper().endswith((".TW", ".TWO"))
    ]
    return us + TW_EXTRA


def _forward_move(close: list[float], b: int, last: int, kind: str) -> float | None:
    """Best move within RALLY_WINDOW after b: max rise (kind='rise') or max drop."""
    end = min(b + RALLY_WINDOW, last)
    if end - b < MIN_FWD:
        return None
    seg = close[b + 1: end + 1]
    base = close[b]
    if base <= 0 or not seg:
        return None
    return (max(seg) / base - 1) if kind == "rise" else (min(seg) / base - 1)


def _qualifying(turns: list[int], close: list[float], last: int, kind: str, thr: float, is_all: bool) -> list[int]:
    if is_all:
        return turns
    out = []
    for b in turns:
        mv = _forward_move(close, b, last, kind)
        if mv is None:
            continue
        if (kind == "rise" and mv >= thr) or (kind == "drop" and mv <= -thr):
            out.append(b)
    return out


def _match(close: list[float], turns: list[int], signals: list[int], order: int, kind: str):
    """Return (n_turns, matched, penalties, gaps) for turns caught within +/- order."""
    sig = sorted(signals)
    matched = 0
    pens: list[float] = []
    gaps: list[int] = []
    for b in turns:
        cands = [s for s in sig if abs(s - b) <= order]
        if not cands:
            continue
        matched += 1
        nearest = min(cands, key=lambda s: abs(s - b))
        base = close[b]
        # penalty = distance from the ideal extreme price, as a positive cost %
        pen = (close[nearest] - base) / base if kind == "rise" else (base - close[nearest]) / base
        pens.append(pen)
        gaps.append(nearest - b)
    return len(turns), matched, pens, gaps


def _in_window(s: int, b: int, w: int, direction: str) -> bool:
    """direction='before': signal in the w days up to the turn (leading/predictive).
    direction='sym': within +/-w of the turn."""
    if direction == "before":
        return b - w <= s <= b
    return abs(s - b) <= w


def _cooc_anchors(conf: list[int], early: list[int], w: int) -> list[int]:
    """'Both' = a confirmed and an early signal within w bars of each other; the
    anchor (entry) is the later of the two so it stays causal."""
    anchors: set[int] = set()
    es = sorted(early)
    for c in conf:
        for e in es:
            if abs(c - e) <= w:
                anchors.add(max(c, e))
    return sorted(anchors)


def _match_dir(close: list[float], turns: list[int], points: list[int], w: int, kind: str, direction: str):
    pts = sorted(points)
    matched = 0
    pens: list[float] = []
    gaps: list[int] = []
    for b in turns:
        cands = [s for s in pts if _in_window(s, b, w, direction)]
        if not cands:
            continue
        matched += 1
        nearest = min(cands, key=lambda s: abs(s - b))
        base = close[b]
        pen = (close[nearest] - base) / base if kind == "rise" else (base - close[nearest]) / base
        pens.append(pen)
        gaps.append(nearest - b)
    return len(turns), matched, pens, gaps


def _precision_dir(points: list[int], turns: list[int], w: int, direction: str) -> tuple[int, int]:
    ts = sorted(turns)
    near = sum(1 for s in points if any(_in_window(s, b, w, direction) for b in ts))
    return len(points), near


def _med(xs: list[float]) -> float:
    return statistics.median(xs) if xs else float("nan")


def main() -> None:
    strat = StrategyD()
    params = {**strat.default_params(), "enable_early_signal": True}

    # acc[(direction, order, tier, group)] = [n_turns, matched, pens, gaps]
    acc: dict[tuple, list] = {}
    # acc_prec[(direction, order, group)] = [n_signals, near_any_turn]
    acc_prec: dict[tuple, list] = {}
    # acc_sweep[(direction, turn_order, window, group)] = [n_turns, matched, pens, gaps, n_sig, near]
    acc_sweep: dict[tuple, list] = {}
    # acc_dir[(side, match_dir, window, group)] = [n_turns, matched, pens, gaps, n_pts, near]
    acc_dir: dict[tuple, list] = {}
    skipped: list[str] = []
    n_tickers = 0

    sides = [("buy", "rise", _swing_low_indices, "low"),
             ("sell", "drop", _swing_high_indices, "high")]

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
        date_to_idx = {str(d)[:10]: i for i, d in enumerate(df["date"].reset_index(drop=True))}
        close = [float(c) for c in df["close"].reset_index(drop=True)]
        last = len(close) - 1

        groups = {"confirmed": {"buy": [], "sell": []},
                  "early": {"buy": [], "sell": []}}
        for s in sigs:
            if s.signal_type not in ("buy", "sell"):
                continue
            idx = date_to_idx.get(s.date)
            if idx is None:
                continue
            groups["early" if s.tier == "early" else "confirmed"][s.signal_type].append(idx)

        for side, kind, finder, col in sides:
            series = df[col].reset_index(drop=True)
            for order in ORDERS:
                turns_all = finder(series, order)
                sig_groups = {
                    "confirmed": groups["confirmed"][side],
                    "early": groups["early"][side],
                    "union": groups["confirmed"][side] + groups["early"][side],
                }
                # precision: how many signals land within +/-order of ANY swing turn
                turn_set = sorted(turns_all)
                for gname, gsig in sig_groups.items():
                    near = sum(1 for s in gsig if any(abs(s - b) <= order for b in turn_set))
                    pa = acc_prec.setdefault((side, order, gname), [0, 0])
                    pa[0] += len(gsig)
                    pa[1] += near
                # match-window sweep: decouple "how close counts as caught" (W) from
                # the turn-definition scale (order). Turns = all swing points at order.
                for w in MATCH_WINDOWS:
                    for gname, gsig in sig_groups.items():
                        n, m, pens, gaps = _match(close, turns_all, gsig, w, kind)
                        near_w = sum(1 for s in gsig if any(abs(s - b) <= w for b in turn_set))
                        sa = acc_sweep.setdefault((side, order, w, gname), [0, 0, [], [], 0, 0])
                        sa[0] += n
                        sa[1] += m
                        sa[2].extend(pens)
                        sa[3].extend(gaps)
                        sa[4] += len(gsig)
                        sa[5] += near_w
                for label, thr in TIERS:
                    turns = _qualifying(turns_all, close, last, kind, thr, label == "all")
                    for gname, gsig in sig_groups.items():
                        n, m, pens, gaps = _match(close, turns, gsig, order, kind)
                        key = (side, order, label, gname)
                        a = acc.setdefault(key, [0, 0, [], []])
                        a[0] += n
                        a[1] += m
                        a[2].extend(pens)
                        a[3].extend(gaps)

            # directional (before-only) + confirmed/early/both comparison @ NEW_TURN_ORDER
            turns_n = finder(series, NEW_TURN_ORDER)
            conf = groups["confirmed"][side]
            earl = groups["early"][side]
            for direction in DIRECTIONS:
                for w in MATCH_WINDOWS:
                    point_groups = {
                        "confirmed": conf,
                        "early": earl,
                        "both": _cooc_anchors(conf, earl, w),
                    }
                    for gname, pts in point_groups.items():
                        n, m, pens, gaps = _match_dir(close, turns_n, pts, w, kind, direction)
                        npts, near = _precision_dir(pts, turns_n, w, direction)
                        a = acc_dir.setdefault((side, direction, w, gname), [0, 0, [], [], 0, 0])
                        a[0] += n
                        a[1] += m
                        a[2].extend(pens)
                        a[3].extend(gaps)
                        a[4] += npts
                        a[5] += near

    print(f"\nUniverse: {n_tickers} tickers, {len(skipped)} skipped")
    print(f"Params: orders={ORDERS}, rally_window={RALLY_WINDOW}td, min_fwd={MIN_FWD}td, YEARS={YEARS}")
    print("recall = turns with a signal within +/-order | med_pen = median price penalty "
          "(how far from the ideal extreme) | med_gap = median (signal-turn) td, +after/-before")

    for side, kind, _, _ in sides:
        label_side = "BUY vs bottoms" if side == "buy" else "SELL vs tops"
        print(f"\n{'=' * 70}\n {label_side}\n{'=' * 70}")
        for order in ORDERS:
            print(f"\n  swing order +/-{order} td")
            print(f"    {'tier':<6}{'turns':>7}{'group':>11}{'recall':>9}{'med_pen':>10}{'med_gap':>9}")
            for label, _thr in TIERS:
                for gname in ("confirmed", "early", "union"):
                    n, m, pens, gaps = acc.get((side, order, label, gname), [0, 0, [], []])
                    recall = m / n if n else float("nan")
                    turns_str = str(n) if gname == "confirmed" else ""
                    tier_str = label if gname == "confirmed" else ""
                    rec_str = f"{recall * 100:.0f}%" if n else "—"
                    pen_str = f"{_med(pens) * 100:+.1f}%" if pens else "—"
                    gap_str = f"{_med(gaps):+.0f}" if gaps else "—"
                    print(f"    {tier_str:<6}{turns_str:>7}{gname:>11}{rec_str:>9}{pen_str:>10}{gap_str:>9}")

        print(f"\n  precision — signals landing within +/-order of ANY swing turn")
        print(f"    {'order':>6}{'group':>11}{'n_sig':>8}{'precision':>11}")
        for order in ORDERS:
            for gname in ("confirmed", "early", "union"):
                n_sig, near = acc_prec.get((side, order, gname), [0, 0])
                prec_str = f"{near / n_sig * 100:.0f}%" if n_sig else "—"
                print(f"    {order:>6}{gname:>11}{n_sig:>8}{prec_str:>11}")

        print(f"\n  match-window sweep — recall & precision as the 'caught' window tightens")
        for order in ORDERS:
            print(f"    turn order +/-{order} td:")
            print(f"      {'W(td)':>6}{'group':>11}{'recall':>9}{'precision':>11}{'med_pen':>10}{'med_gap':>9}")
            for w in MATCH_WINDOWS:
                for gname in ("confirmed", "early", "union"):
                    n, m, pens, gaps, n_sig, near = acc_sweep.get((side, order, w, gname), [0, 0, [], [], 0, 0])
                    rec = f"{m / n * 100:.0f}%" if n else "—"
                    prec = f"{near / n_sig * 100:.0f}%" if n_sig else "—"
                    pen = f"{_med(pens) * 100:+.1f}%" if pens else "—"
                    gap = f"{_med(gaps):+.0f}" if gaps else "—"
                    w_str = str(w) if gname == "confirmed" else ""
                    print(f"      {w_str:>6}{gname:>11}{rec:>9}{prec:>11}{pen:>10}{gap:>9}")

        print(f"\n  confirmed vs early vs BOTH (turn order +/-{NEW_TURN_ORDER} td)")
        print("  'both' = a confirmed AND an early within W of each other; sym=+/-W, before=W days up to the turn")
        for direction in DIRECTIONS:
            dlabel = "symmetric +/-W" if direction == "sym" else "before-only (turn-W .. turn)"
            print(f"    match = {dlabel}")
            print(f"      {'W(td)':>6}{'group':>11}{'recall':>9}{'precision':>11}{'med_pen':>10}{'med_gap':>9}")
            for w in MATCH_WINDOWS:
                for gname in ("confirmed", "early", "both"):
                    n, m, pens, gaps, npts, near = acc_dir.get((side, direction, w, gname), [0, 0, [], [], 0, 0])
                    rec = f"{m / n * 100:.0f}%" if n else "—"
                    prec = f"{near / npts * 100:.0f}%" if npts else "—"
                    pen = f"{_med(pens) * 100:+.1f}%" if pens else "—"
                    gap = f"{_med(gaps):+.0f}" if gaps else "—"
                    w_str = str(w) if gname == "confirmed" else ""
                    print(f"      {w_str:>6}{gname:>11}{rec:>9}{prec:>11}{pen:>10}{gap:>9}")

    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  {s}")


if __name__ == "__main__":
    main()
