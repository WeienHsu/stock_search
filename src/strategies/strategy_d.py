from typing import Any
import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd


def _count_violations(series: pd.Series, ascending: bool) -> int:
    """Count bars that break the expected monotonic direction."""
    count = 0
    for i in range(1, len(series)):
        if ascending:
            if series.iloc[i] <= series.iloc[i - 1]:
                count += 1
        else:
            if series.iloc[i] >= series.iloc[i - 1]:
                count += 1
    return count


# ── Buy helpers ──────────────────────────────────────────────────────────────

def _detect_macd_hist_converging(
    df: pd.DataFrame,
    n_bars: int,
    recovery_pct: float,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> bool:
    """負值直方圖整體遞增並回彈至谷底的 (1-recovery_pct) 倍以內。

    max_violations=0 保留嚴格遞增的舊行為。
    """
    if "histogram" not in df.columns:
        raise ValueError("Missing 'histogram' column. Call add_macd() first.")
    if len(df) < n_bars + 1:
        return False

    hist = df["histogram"].iloc[-(n_bars + 1):]
    if hist.isna().any():
        return False

    recent = hist.iloc[-n_bars:]
    if (recent >= 0).any():
        return False

    if _count_violations(recent, ascending=True) > max_violations:
        return False

    lb = min(lookback_bars, len(df["histogram"]))
    lookback = df["histogram"].iloc[-lb:]
    neg_vals = lookback[lookback < 0]
    if neg_vals.empty:
        return False
    trough = neg_vals.min()
    threshold = abs(trough) * (1 - recovery_pct)
    return abs(recent.iloc[-1]) < threshold


def _build_kd_prefilter_mask(df: pd.DataFrame, window: int, kd_k_threshold: int) -> pd.Series:
    """K 上穿 D 且 K < 閾值（低檔黃金交叉）。"""
    k = df["K"]
    d = df["D"]
    kd_signal = (k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)
    mask = pd.Series(False, index=df.index)
    for offset in range(0, window + 1):
        mask = mask | kd_signal.shift(offset).fillna(False)
    return mask


# ── Sell helpers ─────────────────────────────────────────────────────────────

def _detect_macd_hist_pos_converging(
    df: pd.DataFrame,
    n_bars: int,
    recovery_pct: float,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> bool:
    """正值直方圖整體遞減並回落至峰值的 (1-recovery_pct) 倍以內。

    max_violations=0 保留嚴格遞減的舊行為。
    """
    if "histogram" not in df.columns:
        raise ValueError("Missing 'histogram' column. Call add_macd() first.")
    if len(df) < n_bars + 1:
        return False

    hist = df["histogram"].iloc[-(n_bars + 1):]
    if hist.isna().any():
        return False

    recent = hist.iloc[-n_bars:]
    if (recent <= 0).any():
        return False

    if _count_violations(recent, ascending=False) > max_violations:
        return False

    lb = min(lookback_bars, len(df["histogram"]))
    lookback = df["histogram"].iloc[-lb:]
    pos_vals = lookback[lookback > 0]
    if pos_vals.empty:
        return False
    peak = pos_vals.max()
    threshold = peak * (1 - recovery_pct)
    return recent.iloc[-1] < threshold


def _build_kd_death_cross_mask(df: pd.DataFrame, window: int, kd_d_threshold: int) -> pd.Series:
    """K 下穿 D 且 K > 閾值（高檔死亡交叉）。"""
    k = df["K"]
    d = df["D"]
    kd_signal = (k.shift(1) > d.shift(1)) & (k < d) & (k > kd_d_threshold)
    mask = pd.Series(False, index=df.index)
    for offset in range(0, window + 1):
        mask = mask | kd_signal.shift(offset).fillna(False)
    return mask


# ── Public buy API ────────────────────────────────────────────────────────────

def detect_strategy_d(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 5,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> bool:
    """Return True if Strategy D buy signal fires on the latest bar."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    if not _detect_macd_hist_converging(
        df, n_bars=n_bars, recovery_pct=recovery_pct,
        max_violations=max_violations, lookback_bars=lookback_bars,
    ):
        return False

    window_df = df.iloc[-(kd_window + 1):]
    k = window_df["K"]
    d = window_df["D"]
    kd_fired = ((k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)).any()
    return bool(kd_fired)


def scan_strategy_d(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 5,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> pd.DataFrame:
    """Scan entire history, return DataFrame of all buy signal dates."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    hist = df["histogram"]
    converging_idxs: set[int] = set()

    for i in range(n_bars, len(df)):
        recent = hist.iloc[i - n_bars + 1: i + 1]
        if recent.isna().any():
            continue
        if (recent >= 0).any():
            continue
        if _count_violations(recent, ascending=True) > max_violations:
            continue
        lb_start = max(0, i - (lookback_bars - 1))
        lookback = hist.iloc[lb_start: i + 1]
        neg_vals = lookback[lookback < 0]
        if neg_vals.empty:
            continue
        trough = neg_vals.min()
        threshold = abs(trough) * (1 - recovery_pct)
        if abs(recent.iloc[-1]) < threshold:
            converging_idxs.add(i)

    converging_mask = pd.Series(False, index=df.index)
    if converging_idxs:
        converging_mask.iloc[list(converging_idxs)] = True

    kd_mask = _build_kd_prefilter_mask(df, window=kd_window, kd_k_threshold=kd_k_threshold)
    signal = converging_mask & kd_mask

    cols = [c for c in ["date", "close", "K", "D", "macd_line", "signal_line", "histogram"]
            if c in df.columns]
    return df[signal][cols].reset_index(drop=True)


# ── Public sell API ───────────────────────────────────────────────────────────

def detect_strategy_d_sell(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 5,
    recovery_pct: float = 0.7,
    kd_d_threshold: int = 80,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> bool:
    """Return True if Strategy D sell signal fires on the latest bar."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    if not _detect_macd_hist_pos_converging(
        df, n_bars=n_bars, recovery_pct=recovery_pct,
        max_violations=max_violations, lookback_bars=lookback_bars,
    ):
        return False

    window_df = df.iloc[-(kd_window + 1):]
    k = window_df["K"]
    d = window_df["D"]
    kd_fired = ((k.shift(1) > d.shift(1)) & (k < d) & (k > kd_d_threshold)).any()
    return bool(kd_fired)


def scan_strategy_d_sell(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 5,
    recovery_pct: float = 0.7,
    kd_d_threshold: int = 80,
    max_violations: int = 0,
    lookback_bars: int = 20,
) -> pd.DataFrame:
    """Scan entire history, return DataFrame of all sell signal dates."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    hist = df["histogram"]
    converging_idxs: set[int] = set()

    for i in range(n_bars, len(df)):
        recent = hist.iloc[i - n_bars + 1: i + 1]
        if recent.isna().any():
            continue
        if (recent <= 0).any():
            continue
        if _count_violations(recent, ascending=False) > max_violations:
            continue
        lb_start = max(0, i - (lookback_bars - 1))
        lookback = hist.iloc[lb_start: i + 1]
        pos_vals = lookback[lookback > 0]
        if pos_vals.empty:
            continue
        peak = pos_vals.max()
        threshold = peak * (1 - recovery_pct)
        if recent.iloc[-1] < threshold:
            converging_idxs.add(i)

    converging_mask = pd.Series(False, index=df.index)
    if converging_idxs:
        converging_mask.iloc[list(converging_idxs)] = True

    kd_mask = _build_kd_death_cross_mask(df, window=kd_window, kd_d_threshold=kd_d_threshold)
    signal = converging_mask & kd_mask

    cols = [c for c in ["date", "close", "K", "D", "macd_line", "signal_line", "histogram"]
            if c in df.columns]
    return df[signal][cols].reset_index(drop=True)


def diagnose_strategy_d(
    df: pd.DataFrame,
    date: str,
    params: dict[str, Any],
) -> list[dict] | None:
    """Per-condition buy signal pass/fail analysis for a specific date."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        return None

    date_str = str(date)[:10]
    date_mask = df["date"].astype(str).str[:10] == date_str
    if not date_mask.any():
        return None

    idx = int(df[date_mask].index[-1])
    df_up = df.iloc[: idx + 1]

    n_bars = int(params.get("n_bars", 5))
    recovery_pct = float(params.get("recovery_pct", 0.7))
    kd_window = int(params.get("kd_window", 10))
    kd_k_threshold = int(params.get("kd_k_threshold", 20))
    max_violations = int(params.get("max_violations", 0))
    lookback_bars = int(params.get("lookback_bars", 20))

    # ── MACD 直方圖收斂（負值往上） ──
    macd_ok = False
    macd_summary = "資料不足"
    macd_metrics: list[dict] = []

    if len(df_up) >= n_bars + 1:
        hist = df_up["histogram"]
        recent = hist.iloc[-n_bars:]
        has_nan = recent.isna().any()

        if has_nan:
            macd_summary = "含 NaN，MACD 指標可能尚未暖機"
            macd_metrics = [{"name": "近期直方圖", "actual": "含 NaN", "target": "無 NaN", "passed": False}]
        else:
            all_neg = (recent < 0).all()
            actual_violations = _count_violations(recent, ascending=True)
            shape_ok = actual_violations <= max_violations

            macd_metrics.append({
                "name": f"最近 {n_bars} 根全為負值（綠 BAR）",
                "actual": "是" if all_neg else "否（含正值）",
                "target": "是",
                "passed": all_neg,
            })
            macd_metrics.append({
                "name": f"形狀遞增（違反 ≤ {max_violations} 根）",
                "actual": f"{actual_violations} 根違反",
                "target": f"≤ {max_violations} 根",
                "passed": shape_ok,
            })

            lb = min(lookback_bars, len(hist))
            lookback = hist.iloc[-lb:]
            neg_vals = lookback[lookback < 0]

            if all_neg and not neg_vals.empty:
                trough = float(neg_vals.min())
                current = abs(float(recent.iloc[-1]))
                threshold = abs(trough) * (1 - recovery_pct)
                actual_recovery = 1.0 - current / abs(trough) if trough != 0 else 0.0
                recovery_passed = current < threshold
                macd_ok = all_neg and shape_ok and recovery_passed
                progress = max(0.0, min(actual_recovery / recovery_pct, 1.0)) if recovery_pct > 0 else 0.0
                macd_metrics.append({
                    "name": "MACD 回彈比例",
                    "actual": actual_recovery,
                    "target": recovery_pct,
                    "unit": "%",
                    "comparison": "≥",
                    "passed": recovery_passed,
                    "progress": progress,
                })
                macd_summary = (
                    f"最近 {n_bars} 根：{', '.join(f'{v:.4f}' for v in recent.tolist())}｜"
                    f"谷底 {trough:.4f}（回看 {lookback_bars} 根）｜"
                    f"恢復比例 {actual_recovery:.1%}（需 ≥ {recovery_pct:.0%}）｜"
                    f"違反 {actual_violations}/{max_violations} 根"
                )
            elif not all_neg:
                macd_summary = f"最近 {n_bars} 根直方圖含非負值（需全部為負值）"
            else:
                macd_summary = f"近期 {lookback_bars} 根無負值直方圖可計算谷底"
    else:
        macd_metrics = [{"name": "資料量", "actual": f"{len(df_up)} 根", "target": f"≥ {n_bars + 1} 根", "passed": False}]

    # ── KD 黃金交叉 ──
    kd_ok = False
    kd_summary = "資料不足"
    kd_metrics: list[dict] = []

    if len(df_up) >= 2:
        k = df_up["K"]
        d = df_up["D"]
        kd_cross_signal = (k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)
        window_cross = kd_cross_signal.iloc[-(kd_window + 1):]
        kd_ok = bool(window_cross.any())
        k_val = float(k.iloc[-1])
        d_val = float(d.iloc[-1])
        cross_anywhere = ((k.shift(1) < d.shift(1)) & (k > d)).iloc[-(kd_window + 1):].any()

        kd_metrics.append({
            "name": f"近 {kd_window} 根有 KD 黃金交叉",
            "actual": "是" if cross_anywhere else "否",
            "target": "是",
            "passed": bool(cross_anywhere),
        })
        kd_metrics.append({
            "name": "K 值（需低於閾值，低檔超賣）",
            "actual": k_val,
            "target": float(kd_k_threshold),
            "unit": "",
            "comparison": "<",
            "passed": k_val < kd_k_threshold,
            "progress": min(kd_k_threshold / max(k_val, 0.01), 1.0),
        })
        kd_metrics.append({
            "name": "D 值（參考）",
            "actual": d_val,
            "target": "—",
            "unit": "",
        })

        if kd_ok:
            kd_summary = (
                f"K={k_val:.1f}, D={d_val:.1f}｜"
                f"最近 {kd_window} 根內有黃金交叉且 K < {kd_k_threshold}"
            )
        else:
            if not cross_anywhere:
                reason = f"最近 {kd_window} 根內無 KD 黃金交叉"
            elif k_val >= kd_k_threshold:
                reason = f"K={k_val:.1f} ≥ 閾值 {kd_k_threshold}"
            else:
                reason = f"交叉時 K ≥ 閾值 {kd_k_threshold}"
            kd_summary = f"K={k_val:.1f}, D={d_val:.1f}｜{reason}"
    else:
        kd_metrics = [{"name": "資料量", "actual": f"{len(df_up)} 根", "target": "≥ 2 根", "passed": False}]

    return [
        {
            "condition": "MACD 綠 BAR 收斂（往零軸縮減）",
            "passed": macd_ok,
            "metrics": macd_metrics,
            "summary": macd_summary,
        },
        {
            "condition": f"KD 黃金交叉（低檔，回看 {kd_window} 根，K < {kd_k_threshold}）",
            "passed": kd_ok,
            "metrics": kd_metrics,
            "summary": kd_summary,
        },
    ]


def diagnose_strategy_d_sell(
    df: pd.DataFrame,
    date: str,
    params: dict[str, Any],
) -> list[dict] | None:
    """Per-condition sell signal pass/fail analysis for a specific date."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        return None

    date_str = str(date)[:10]
    date_mask = df["date"].astype(str).str[:10] == date_str
    if not date_mask.any():
        return None

    idx = int(df[date_mask].index[-1])
    df_up = df.iloc[: idx + 1]

    n_bars = int(params.get("n_bars", 5))
    recovery_pct = float(params.get("recovery_pct", 0.7))
    kd_window = int(params.get("kd_window", 10))
    kd_d_threshold = int(params.get("kd_d_threshold", 80))
    max_violations = int(params.get("max_violations", 0))
    lookback_bars = int(params.get("lookback_bars", 20))

    # ── MACD 直方圖收斂（正值往下） ──
    macd_ok = False
    macd_summary = "資料不足"
    macd_metrics: list[dict] = []

    if len(df_up) >= n_bars + 1:
        hist = df_up["histogram"]
        recent = hist.iloc[-n_bars:]
        has_nan = recent.isna().any()

        if has_nan:
            macd_summary = "含 NaN，MACD 指標可能尚未暖機"
            macd_metrics = [{"name": "近期直方圖", "actual": "含 NaN", "target": "無 NaN", "passed": False}]
        else:
            all_pos = (recent > 0).all()
            actual_violations = _count_violations(recent, ascending=False)
            shape_ok = actual_violations <= max_violations

            macd_metrics.append({
                "name": f"最近 {n_bars} 根全為正值（紅 BAR）",
                "actual": "是" if all_pos else "否（含負值）",
                "target": "是",
                "passed": all_pos,
            })
            macd_metrics.append({
                "name": f"形狀遞減（違反 ≤ {max_violations} 根）",
                "actual": f"{actual_violations} 根違反",
                "target": f"≤ {max_violations} 根",
                "passed": shape_ok,
            })

            lb = min(lookback_bars, len(hist))
            lookback = hist.iloc[-lb:]
            pos_vals = lookback[lookback > 0]

            if all_pos and not pos_vals.empty:
                peak = float(pos_vals.max())
                current = float(recent.iloc[-1])
                threshold = peak * (1 - recovery_pct)
                actual_recovery = 1.0 - current / peak if peak != 0 else 0.0
                recovery_passed = current < threshold
                macd_ok = all_pos and shape_ok and recovery_passed
                progress = max(0.0, min(actual_recovery / recovery_pct, 1.0)) if recovery_pct > 0 else 0.0
                macd_metrics.append({
                    "name": "MACD 回落比例",
                    "actual": actual_recovery,
                    "target": recovery_pct,
                    "unit": "%",
                    "comparison": "≥",
                    "passed": recovery_passed,
                    "progress": progress,
                })
                macd_summary = (
                    f"最近 {n_bars} 根：{', '.join(f'{v:.4f}' for v in recent.tolist())}｜"
                    f"峰值 {peak:.4f}（回看 {lookback_bars} 根）｜"
                    f"回落比例 {actual_recovery:.1%}（需 ≥ {recovery_pct:.0%}）｜"
                    f"違反 {actual_violations}/{max_violations} 根"
                )
            elif not all_pos:
                macd_summary = f"最近 {n_bars} 根直方圖含非正值（需全部為正值）"
            else:
                macd_summary = f"近期 {lookback_bars} 根無正值直方圖可計算峰值"
    else:
        macd_metrics = [{"name": "資料量", "actual": f"{len(df_up)} 根", "target": f"≥ {n_bars + 1} 根", "passed": False}]

    # ── KD 死亡交叉 ──
    kd_ok = False
    kd_summary = "資料不足"
    kd_metrics: list[dict] = []

    if len(df_up) >= 2:
        k = df_up["K"]
        d = df_up["D"]
        kd_cross_signal = (k.shift(1) > d.shift(1)) & (k < d) & (k > kd_d_threshold)
        window_cross = kd_cross_signal.iloc[-(kd_window + 1):]
        kd_ok = bool(window_cross.any())
        k_val = float(k.iloc[-1])
        d_val = float(d.iloc[-1])
        cross_anywhere = ((k.shift(1) > d.shift(1)) & (k < d)).iloc[-(kd_window + 1):].any()

        kd_metrics.append({
            "name": f"近 {kd_window} 根有 KD 死亡交叉",
            "actual": "是" if cross_anywhere else "否",
            "target": "是",
            "passed": bool(cross_anywhere),
        })
        kd_metrics.append({
            "name": "K 值（需高於閾值，高檔超買）",
            "actual": k_val,
            "target": float(kd_d_threshold),
            "unit": "",
            "comparison": ">",
            "passed": k_val > kd_d_threshold,
            "progress": min(k_val / max(kd_d_threshold, 0.01), 1.0),
        })
        kd_metrics.append({
            "name": "D 值（參考）",
            "actual": d_val,
            "target": "—",
            "unit": "",
        })

        if kd_ok:
            kd_summary = (
                f"K={k_val:.1f}, D={d_val:.1f}｜"
                f"最近 {kd_window} 根內有死亡交叉且 K > {kd_d_threshold}"
            )
        else:
            if not cross_anywhere:
                reason = f"最近 {kd_window} 根內無 KD 死亡交叉"
            elif k_val <= kd_d_threshold:
                reason = f"K={k_val:.1f} ≤ 閾值 {kd_d_threshold}"
            else:
                reason = f"交叉時 K ≤ 閾值 {kd_d_threshold}"
            kd_summary = f"K={k_val:.1f}, D={d_val:.1f}｜{reason}"
    else:
        kd_metrics = [{"name": "資料量", "actual": f"{len(df_up)} 根", "target": "≥ 2 根", "passed": False}]

    return [
        {
            "condition": "MACD 紅 BAR 收斂（往零軸縮減）",
            "passed": macd_ok,
            "metrics": macd_metrics,
            "summary": macd_summary,
        },
        {
            "condition": f"KD 死亡交叉（高檔，回看 {kd_window} 根，K > {kd_d_threshold}）",
            "passed": kd_ok,
            "metrics": kd_metrics,
            "summary": kd_summary,
        },
    ]


def prepare_df(df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
    """Add all indicators needed for Strategy D."""
    df = add_macd(df,
                  fast=params.get("macd_fast", 12),
                  slow=params.get("macd_slow", 26),
                  signal=params.get("macd_signal", 9))
    df = add_kd(df,
                k=params.get("kd_k", 9),
                d=params.get("kd_d", 3),
                smooth_k=params.get("kd_smooth_k", 3))
    return df


class StrategyD(StrategyBase):
    strategy_id = "strategy_d"

    def default_params(self) -> dict[str, Any]:
        return {
            "kd_window": 10,
            "n_bars": 3,
            "recovery_pct": 0.7,
            "kd_k_threshold": 20,
            "kd_d_threshold": 80,
            "max_violations": 0,
            "lookback_bars": 20,
            "enable_sell_signal": True,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "kd_k": 9,
            "kd_d": 3,
            "kd_smooth_k": 3,
        }

    def compute(self, df: pd.DataFrame, params: dict[str, Any]) -> list[Signal]:
        p = {**self.default_params(), **params}
        df = prepare_df(df, p)

        signals: list[Signal] = []

        buy_df = scan_strategy_d(
            df,
            kd_window=p["kd_window"],
            n_bars=p["n_bars"],
            recovery_pct=p["recovery_pct"],
            kd_k_threshold=p["kd_k_threshold"],
            max_violations=p["max_violations"],
            lookback_bars=p["lookback_bars"],
        )
        for _, row in buy_df.iterrows():
            signals.append(Signal(
                date=str(row["date"])[:10] if "date" in row else "",
                signal_type="buy",
                strategy_id=self.strategy_id,
                metadata={"close": float(row.get("close", 0))},
            ))

        if p.get("enable_sell_signal", True):
            sell_df = scan_strategy_d_sell(
                df,
                kd_window=p["kd_window"],
                n_bars=p["n_bars"],
                recovery_pct=p["recovery_pct"],
                kd_d_threshold=p["kd_d_threshold"],
                max_violations=p["max_violations"],
                lookback_bars=p["lookback_bars"],
            )
            for _, row in sell_df.iterrows():
                signals.append(Signal(
                    date=str(row["date"])[:10] if "date" in row else "",
                    signal_type="sell",
                    strategy_id=self.strategy_id,
                    metadata={"close": float(row.get("close", 0))},
                ))

        return signals


register("strategy_d", StrategyD)
