from __future__ import annotations

import json
from typing import Any

from src.ai.provider_chain import AIProviderChain
from src.ai.providers.base import AIMessage

SYSTEM_PROMPT = (
    "你是投資組合週報助理。請用繁體中文，整理客觀事件與訊號，不做保證獲利承諾。"
)


def build_weekly_digest_messages(rows: list[dict[str, Any]]) -> list[AIMessage]:
    payload = json.dumps(rows, ensure_ascii=False, default=str)
    prompt = f"""
請根據 watchlist 過去一週策略觸發與報酬資料，產出一封中文週報：
1. 本週總覽。
2. 重要訊號股票。
3. 風險提醒。
4. 下週觀察清單。

資料：
{payload}
""".strip()
    return [{"role": "user", "content": prompt}]


def generate_weekly_digest(chain: AIProviderChain, rows: list[dict[str, Any]]) -> str:
    return chain.generate(
        build_weekly_digest_messages(rows),
        system=SYSTEM_PROMPT,
        temperature=0.25,
    )
