from __future__ import annotations

from typing import Any

import pandas as pd

import src.strategies.strategy_d  # ensure registration
import src.strategies.strategy_kd  # ensure registration

from src.ai.prompts.weekly_digest import generate_weekly_digest
from src.ai.provider_chain import build_default_chain
from src.auth.auth_manager import list_users
from src.core.strategy_registry import get as get_strategy
from src.data.price_fetcher import fetch_prices_for_strategy
from src.data.ticker_utils import normalize_ticker
from src.notifications import send_notification
from src.repositories.scheduler_run_repo import finish_run, start_run
from src.repositories.watchlist_repo import get_watchlist

JOB_NAME = "weekly_digest"


def run_weekly_digest() -> dict[str, Any]:
    run_id = start_run(JOB_NAME)
    users_checked = 0
    digests_sent = 0
    ai_generated = 0
    try:
        for user in list_users():
            users_checked += 1
            user_id = user["user_id"]
            items = get_watchlist(user_id)
            if not items:
                continue

            rows = build_weekly_digest_rows(items)
            body, used_ai = build_weekly_digest_body(user_id, rows)
            send_notification(
                user_id,
                "每週投資組合週報",
                body,
                severity="info",
                event_type="weekly_digest",
            )
            digests_sent += 1
            ai_generated += 1 if used_ai else 0

        finish_run(run_id, "success")
        return {
            "users_checked": users_checked,
            "digests_sent": digests_sent,
            "ai_generated": ai_generated,
        }
    except Exception as exc:
        finish_run(run_id, "failed", error=str(exc))
        raise


def build_weekly_digest_rows(
    items: list[dict[str, Any]],
    *,
    strategy_id: str = "strategy_d",
    strategy_params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    strategy = get_strategy(strategy_id)
    params = {**strategy.default_params(), **(strategy_params or {})}
    rows: list[dict[str, Any]] = []
    for item in items:
        ticker = normalize_ticker(str(item.get("ticker", "")))
        name = str(item.get("name", ""))
        if not ticker:
            continue
        try:
            df = fetch_prices_for_strategy(ticker, years=1)
            if df.empty:
                rows.append(_error_row(ticker, name, "無價格資料"))
                continue
            rows.append(_digest_row(ticker, name, df, strategy, params))
        except Exception as exc:
            rows.append(_error_row(ticker, name, str(exc)[:80]))
    return rows


def build_weekly_digest_body(user_id: str, rows: list[dict[str, Any]]) -> tuple[str, bool]:
    if rows:
        try:
            body = generate_weekly_digest(build_default_chain(user_id), rows)
            if body.strip():
                return body.strip(), True
        except Exception:
            pass
    return fallback_weekly_digest_body(rows), False


def fallback_weekly_digest_body(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "本週 watchlist 沒有可整理的股票。"
    lines = [
        "本週投資組合週報",
        "",
        "本週總覽：",
    ]
    valid_returns = [
        float(row["weekly_return_pct"])
        for row in rows
        if isinstance(row.get("weekly_return_pct"), (int, float))
    ]
    if valid_returns:
        avg_return = sum(valid_returns) / len(valid_returns)
        lines.append(f"- 可計算股票 {len(valid_returns)} 檔，平均週報酬 {avg_return:+.2f}%。")
    else:
        lines.append("- 本週沒有足夠價格資料可計算週報酬。")

    lines.extend(["", "個股摘要："])
    for row in rows:
        if row.get("error"):
            lines.append(f"- {row['ticker']} {row.get('name', '')}: {row['error']}")
            continue
        lines.append(
            "- {ticker} {name}: {start_close:.2f} -> {current_close:.2f}, "
            "週報酬 {weekly_return_pct:+.2f}%，當週訊號：{recent_signals}".format(
                ticker=row["ticker"],
                name=row.get("name", ""),
                start_close=float(row["start_close"]),
                current_close=float(row["current_close"]),
                weekly_return_pct=float(row["weekly_return_pct"]),
                recent_signals=row.get("recent_signals") or "無",
            )
        )
    lines.extend([
        "",
        "風險提醒：以上為系統依 watchlist、價格與策略訊號整理的客觀摘要，不代表獲利保證。",
    ])
    return "\n".join(lines)


def _digest_row(ticker: str, name: str, df: pd.DataFrame, strategy, params: dict[str, Any]) -> dict[str, Any]:
    clean_df = df.dropna(subset=["close"]).reset_index(drop=True)
    if clean_df.empty:
        return _error_row(ticker, name, "無有效收盤價")

    window = clean_df.tail(6)
    start = window.iloc[0]
    latest = window.iloc[-1]
    start_close = float(start["close"])
    current_close = float(latest["close"])
    weekly_return_pct = ((current_close / start_close) - 1) * 100 if start_close else 0.0

    signals = strategy.compute(clean_df, params)
    latest_date = pd.to_datetime(str(latest["date"])[:10], errors="coerce")
    cutoff = latest_date - pd.Timedelta(days=7) if not pd.isna(latest_date) else None
    recent = []
    for signal in signals:
        signal_date = pd.to_datetime(str(signal.date)[:10], errors="coerce")
        if cutoff is not None and not pd.isna(signal_date) and signal_date >= cutoff:
            recent.append(signal)

    buy_dates = [signal.date[:10] for signal in signals if signal.signal_type == "buy"]
    sell_dates = [signal.date[:10] for signal in signals if signal.signal_type == "sell"]
    return {
        "ticker": ticker,
        "name": name,
        "week_start": str(start["date"])[:10],
        "week_end": str(latest["date"])[:10],
        "start_close": round(start_close, 2),
        "current_close": round(current_close, 2),
        "weekly_return_pct": round(weekly_return_pct, 2),
        "recent_signals": _format_recent_signals(recent),
        "last_buy_date": max(buy_dates) if buy_dates else "—",
        "last_sell_date": max(sell_dates) if sell_dates else "—",
    }


def _format_recent_signals(signals: list) -> str:
    if not signals:
        return "無"
    labels = {"buy": "買進", "sell": "賣出"}
    return "、".join(
        f"{labels.get(signal.signal_type, signal.signal_type)} {str(signal.date)[:10]}"
        for signal in sorted(signals, key=lambda item: item.date)
    )


def _error_row(ticker: str, name: str, error: str) -> dict[str, Any]:
    return {"ticker": ticker, "name": name, "error": error}
