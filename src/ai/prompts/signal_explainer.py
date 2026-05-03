from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.ai.provider_chain import AIProviderChain
from src.ai.providers.base import AIMessage

SYSTEM_PROMPT = (
    "你是股票技術分析助理。請用繁體中文回答，重點是解釋訊號成因、風險和觀察點。"
    "不要保證獲利，不要給絕對買賣建議；若資料不足要明確說明。"
)


def build_signal_explainer_messages(context: dict[str, Any]) -> list[AIMessage]:
    payload = json.dumps(context, ensure_ascii=False, default=str)
    prompt = f"""
請根據以下資料解讀目前股票訊號。

輸出格式：
1. 目前訊號判讀：一句話說明買進/賣出/無訊號狀態。
2. 技術面原因：用 2-4 點說明 MACD、KD、BIAS、均線或價格結構。
3. 風險與觀察：列出 2-3 個接下來要注意的條件。
4. 實務結論：用保守語氣說明是否適合觀察、等待或需要更多確認。

資料：
{payload}
""".strip()
    return [{"role": "user", "content": prompt}]


def build_signal_context(
    ticker: str,
    df: pd.DataFrame,
    signal_layers: list[Any],
    today_buy: bool,
    today_sell: bool,
) -> dict[str, Any]:
    columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ma_5",
        "ma_10",
        "ma_20",
        "ma_60",
        "macd_line",
        "signal_line",
        "histogram",
        "K",
        "D",
        "bias",
    ]
    available = [col for col in columns if col in df.columns]
    recent = df[available].tail(60).copy()
    for col in recent.select_dtypes(include="number").columns:
        recent[col] = recent[col].round(4)

    signals = []
    for layer in signal_layers:
        signals.append({
            "strategy": getattr(layer, "label", getattr(layer, "strategy_id", "unknown")),
            "recent_buy_dates": list(getattr(layer, "buy_dates", [])[-8:]),
            "recent_sell_dates": list(getattr(layer, "sell_dates", [])[-8:]),
        })

    latest = recent.tail(1).to_dict("records")
    return {
        "ticker": ticker,
        "today_buy_signal": today_buy,
        "today_sell_signal": today_sell,
        "latest_bar": latest[0] if latest else {},
        "recent_bars": recent.to_dict("records"),
        "strategy_signals": signals,
    }


def generate_signal_explanation(
    chain: AIProviderChain,
    ticker: str,
    df: pd.DataFrame,
    signal_layers: list[Any],
    today_buy: bool,
    today_sell: bool,
) -> str:
    context = build_signal_context(ticker, df, signal_layers, today_buy, today_sell)
    return chain.generate(
        build_signal_explainer_messages(context),
        system=SYSTEM_PROMPT,
        temperature=0.2,
    )
