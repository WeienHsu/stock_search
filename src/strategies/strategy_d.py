from typing import Any
import pandas as pd

from src.core.strategy_base import Signal, StrategyBase
from src.core.strategy_registry import register
from src.indicators.macd import add_macd
from src.indicators.kd import add_kd


# ── Buy helpers ──────────────────────────────────────────────────────────────

def _detect_macd_hist_converging(df: pd.DataFrame, n_bars: int, recovery_pct: float) -> bool:
    """負值直方圖嚴格遞增並回彈至谷底的 (1-recovery_pct) 倍以內。"""
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

    for i in range(1, len(recent)):
        if recent.iloc[i] <= recent.iloc[i - 1]:
            return False

    lookback = df["histogram"].iloc[-20:] if len(df) >= 20 else df["histogram"]
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

def _detect_macd_hist_pos_converging(df: pd.DataFrame, n_bars: int, recovery_pct: float) -> bool:
    """正值直方圖嚴格遞減並回落至峰值的 (1-recovery_pct) 倍以內。"""
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

    for i in range(1, len(recent)):
        if recent.iloc[i] >= recent.iloc[i - 1]:
            return False

    lookback = df["histogram"].iloc[-20:] if len(df) >= 20 else df["histogram"]
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
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
) -> bool:
    """Return True if Strategy D buy signal fires on the latest bar."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    if not _detect_macd_hist_converging(df, n_bars=n_bars, recovery_pct=recovery_pct):
        return False

    window_df = df.iloc[-(kd_window + 1):]
    k = window_df["K"]
    d = window_df["D"]
    kd_fired = ((k.shift(1) < d.shift(1)) & (k > d) & (k < kd_k_threshold)).any()
    return bool(kd_fired)


def scan_strategy_d(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_k_threshold: int = 20,
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
        converging = all(recent.iloc[j] > recent.iloc[j - 1] for j in range(1, len(recent)))
        if not converging:
            continue
        lb_start = max(0, i - 19)
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
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_d_threshold: int = 80,
) -> bool:
    """Return True if Strategy D sell signal fires on the latest bar."""
    required = {"K", "D", "histogram"}
    if not required.issubset(df.columns):
        raise ValueError("Missing required columns. Call add_macd() and add_kd() first.")

    if not _detect_macd_hist_pos_converging(df, n_bars=n_bars, recovery_pct=recovery_pct):
        return False

    window_df = df.iloc[-(kd_window + 1):]
    k = window_df["K"]
    d = window_df["D"]
    kd_fired = ((k.shift(1) > d.shift(1)) & (k < d) & (k > kd_d_threshold)).any()
    return bool(kd_fired)


def scan_strategy_d_sell(
    df: pd.DataFrame,
    kd_window: int = 10,
    n_bars: int = 3,
    recovery_pct: float = 0.7,
    kd_d_threshold: int = 80,
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
        converging = all(recent.iloc[j] < recent.iloc[j - 1] for j in range(1, len(recent)))
        if not converging:
            continue
        lb_start = max(0, i - 19)
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

    n_bars = int(params.get("n_bars", 3))
    recovery_pct = float(params.get("recovery_pct", 0.7))
    kd_window = int(params.get("kd_window", 10))
    kd_k_threshold = int(params.get("kd_k_threshold", 20))

    # ── MACD 直方圖收斂（負值往上） ──
    macd_ok = False
    macd_summary = "資料不足"
    macd_metrics: list[dict] = []

    if len(df_up) >= n_bars + 1:
        hist = df_up["histogram"]
        recent = hist.iloc[-n_bars:]
        has_nan = recent.isna().any()
        all_neg = not has_nan and (recent < 0).all()
        converging = all(recent.iloc[j] > recent.iloc[j - 1] for j in range(1, n_bars)) if n_bars > 1 else True

        if has_nan:
            macd_summary = "含 NaN，MACD 指標可能尚未暖機"
            macd_metrics = [{"name": "近期直方圖", "actual": "含 NaN", "target": "無 NaN", "passed": False}]
        else:
            macd_metrics.append({
                "name": f"最近 {n_bars} 根全為負值（綠 BAR）",
                "actual": "是" if all_neg else "否（含正值）",
                "target": "是",
                "passed": all_neg,
            })
            macd_metrics.append({
                "name": "嚴格遞增收斂（往零軸縮減）",
                "actual": "是" if converging else "否",
                "target": "是",
                "passed": converging,
            })

            lookback = hist.iloc[-20:] if len(hist) >= 20 else hist
            neg_vals = lookback[lookback < 0]

            if all_neg and converging and not neg_vals.empty:
                trough = float(neg_vals.min())
                current = abs(float(recent.iloc[-1]))
                threshold = abs(trough) * (1 - recovery_pct)
                actual_recovery = 1.0 - current / abs(trough) if trough != 0 else 0.0
                macd_ok = current < threshold
                progress = max(0.0, min(actual_recovery / recovery_pct, 1.0)) if recovery_pct > 0 else 0.0
                macd_metrics.append({
                    "name": "MACD 回彈比例",
                    "actual": actual_recovery,
                    "target": recovery_pct,
                    "unit": "%",
                    "comparison": "≥",
                    "passed": macd_ok,
                    "progress": progress,
                })
                macd_summary = (
                    f"最近 {n_bars} 根：{', '.join(f'{v:.4f}' for v in recent.tolist())}｜"
                    f"谷底 {trough:.4f}｜恢復比例 {actual_recovery:.1%}（需 ≥ {recovery_pct:.0%}）"
                )
            elif not all_neg:
                macd_summary = f"最近 {n_bars} 根直方圖含非負值（需全部為負值）"
            elif not converging:
                macd_summary = f"最近 {n_bars} 根直方圖未持續收斂（未嚴格遞增）"
            else:
                macd_summary = "近期無負值直方圖可計算谷底"
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

    n_bars = int(params.get("n_bars", 3))
    recovery_pct = float(params.get("recovery_pct", 0.7))
    kd_window = int(params.get("kd_window", 10))
    kd_d_threshold = int(params.get("kd_d_threshold", 80))

    # ── MACD 直方圖收斂（正值往下） ──
    macd_ok = False
    macd_summary = "資料不足"
    macd_metrics: list[dict] = []

    if len(df_up) >= n_bars + 1:
        hist = df_up["histogram"]
        recent = hist.iloc[-n_bars:]
        has_nan = recent.isna().any()
        all_pos = not has_nan and (recent > 0).all()
        converging = all(recent.iloc[j] < recent.iloc[j - 1] for j in range(1, n_bars)) if n_bars > 1 else True

        if has_nan:
            macd_summary = "含 NaN，MACD 指標可能尚未暖機"
            macd_metrics = [{"name": "近期直方圖", "actual": "含 NaN", "target": "無 NaN", "passed": False}]
        else:
            macd_metrics.append({
                "name": f"最近 {n_bars} 根全為正值（紅 BAR）",
                "actual": "是" if all_pos else "否（含負值）",
                "target": "是",
                "passed": all_pos,
            })
            macd_metrics.append({
                "name": "嚴格遞減收斂（往零軸縮減）",
                "actual": "是" if converging else "否",
                "target": "是",
                "passed": converging,
            })

            lookback = hist.iloc[-20:] if len(hist) >= 20 else hist
            pos_vals = lookback[lookback > 0]

            if all_pos and converging and not pos_vals.empty:
                peak = float(pos_vals.max())
                current = float(recent.iloc[-1])
                threshold = peak * (1 - recovery_pct)
                actual_recovery = 1.0 - current / peak if peak != 0 else 0.0
                macd_ok = current < threshold
                progress = max(0.0, min(actual_recovery / recovery_pct, 1.0)) if recovery_pct > 0 else 0.0
                macd_metrics.append({
                    "name": "MACD 回落比例",
                    "actual": actual_recovery,
                    "target": recovery_pct,
                    "unit": "%",
                    "comparison": "≥",
                    "passed": macd_ok,
                    "progress": progress,
                })
                macd_summary = (
                    f"最近 {n_bars} 根：{', '.join(f'{v:.4f}' for v in recent.tolist())}｜"
                    f"峰值 {peak:.4f}｜回落比例 {actual_recovery:.1%}（需 ≥ {recovery_pct:.0%}）"
                )
            elif not all_pos:
                macd_summary = f"最近 {n_bars} 根直方圖含非正值（需全部為正值）"
            elif not converging:
                macd_summary = f"最近 {n_bars} 根直方圖未持續收斂（未嚴格遞減）"
            else:
                macd_summary = "近期無正值直方圖可計算峰值"
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
