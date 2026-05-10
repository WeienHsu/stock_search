from __future__ import annotations

import json
from typing import Any

from src.ai.provider_chain import AIProviderChain
from src.ai.providers.base import AIMessage

SYSTEM_PROMPT = (
    "你是台股與美股盤前／盤後投資助理。"
    "請用繁體中文，以條列方式整理重點，文字精簡、客觀，不做獲利保證，不臆測走勢。"
    "每個 ticker 的走勢需基於提供的資料，不補入未提供的事實。"
)

_PRE_MARKET_TEMPLATE = """
請根據自選清單昨日收盤資料，生成盤前摘要：
1. **昨日概況**（漲跌前三名）
2. **今日觀察重點**（有訊號的股票或異常量價，條列 3 項以內）
3. **操作提醒**（風險提示，一句話）

資料（ticker / name / date / close / day_change_pct / volume）：
{payload}
""".strip()

_POST_MARKET_TEMPLATE = """
請根據自選清單今日收盤資料，生成盤後摘要：
1. **今日漲跌覆盤**（漲跌前三名）
2. **隔日觀察重點**（條列 3 項以內，可含支撐壓力、量能）
3. **風險提醒**（一句話）

資料（ticker / name / date / close / day_change_pct / volume）：
{payload}
""".strip()


def build_pre_market_messages(rows: list[dict[str, Any]]) -> list[AIMessage]:
    payload = json.dumps(rows, ensure_ascii=False, default=str)
    return [{"role": "user", "content": _PRE_MARKET_TEMPLATE.format(payload=payload)}]


def build_post_market_messages(rows: list[dict[str, Any]]) -> list[AIMessage]:
    payload = json.dumps(rows, ensure_ascii=False, default=str)
    return [{"role": "user", "content": _POST_MARKET_TEMPLATE.format(payload=payload)}]


def generate_daily_digest(
    chain: AIProviderChain,
    rows: list[dict[str, Any]],
    digest_type: str,
) -> str:
    """Generate a daily digest string via AI chain. digest_type: 'pre_market' | 'post_market'."""
    if digest_type == "post_market":
        messages = build_post_market_messages(rows)
    else:
        messages = build_pre_market_messages(rows)
    return chain.generate(messages, system=SYSTEM_PROMPT, temperature=0.3)
