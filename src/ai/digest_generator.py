from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from src.ai.prompts.daily_digest import generate_daily_digest
from src.ai.provider_chain import AIProviderChain, build_default_chain
from src.data.price_fetcher import fetch_prices
from src.repositories.watchlist_repo import get_watchlist


def build_digest_rows(
    user_id: str,
    _price_fn: Callable[[str, str], pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    """Assemble watchlist price rows for digest generation.

    Args:
        user_id: user identifier
        _price_fn: injectable price fetcher for tests; signature (ticker, period) -> DataFrame
    """
    if _price_fn is None:
        _price_fn = lambda ticker, period: fetch_prices(ticker, period=period)

    items = get_watchlist(user_id)
    rows: list[dict[str, Any]] = []
    for item in items:
        ticker = str(item.get("ticker") or "").strip().upper()
        name = str(item.get("name") or "")
        if not ticker:
            continue
        try:
            df = _price_fn(ticker, "1M")
            if df.empty or "close" not in df.columns:
                rows.append({"ticker": ticker, "name": name, "error": "無資料"})
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else None
            day_change_pct = (
                ((float(latest["close"]) / float(prev["close"])) - 1) * 100
                if prev is not None else 0.0
            )
            rows.append({
                "ticker": ticker,
                "name": name,
                "date": str(latest["date"])[:10],
                "close": round(float(latest["close"]), 2),
                "day_change_pct": round(day_change_pct, 2),
                "volume": int(latest.get("volume", 0)),
            })
        except Exception as exc:
            rows.append({"ticker": ticker, "name": name, "error": str(exc)[:80]})
    return rows


def run_digest(
    user_id: str,
    digest_type: str,
    chain: AIProviderChain | None = None,
    _price_fn: Callable | None = None,
) -> tuple[str, bool]:
    """Generate daily digest content for a user.

    Returns:
        (content, used_ai): content is the digest text, used_ai is True if AI was used.
    """
    if chain is None:
        chain = build_default_chain(user_id)

    rows = build_digest_rows(user_id, _price_fn=_price_fn)
    if not rows:
        return "自選清單為空，無法生成摘要。", False

    try:
        content = generate_daily_digest(chain, rows, digest_type)
        if content.strip():
            return content.strip(), True
    except Exception:
        pass

    return _fallback_digest(rows, digest_type), False


def _fallback_digest(rows: list[dict[str, Any]], digest_type: str) -> str:
    """Plain-text fallback when AI is unavailable."""
    title = "盤前摘要" if digest_type == "pre_market" else "盤後摘要"
    valid = [r for r in rows if "close" in r and "day_change_pct" in r]
    if not valid:
        return f"{title}：自選清單無可用資料。"

    sorted_rows = sorted(valid, key=lambda r: abs(r["day_change_pct"]), reverse=True)
    lines = [f"【{title}】自選清單摘要", ""]
    for row in sorted_rows[:5]:
        direction = "▲" if row["day_change_pct"] > 0 else "▼" if row["day_change_pct"] < 0 else "─"
        lines.append(
            f"  {row['ticker']} {row.get('name', '')} "
            f"{direction} {row['day_change_pct']:+.2f}%  收 {row['close']:.2f}"
        )
    lines.append("")
    lines.append("以上為系統依 watchlist 價格資料自動整理，不代表操作建議。")
    return "\n".join(lines)
