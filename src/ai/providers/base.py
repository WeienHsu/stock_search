from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict


class AIMessage(TypedDict):
    role: str
    content: str


class AIProviderError(RuntimeError):
    pass


class MissingAIProviderConfig(AIProviderError):
    pass


class AIProvider(ABC):
    name: str

    @abstractmethod
    def generate(
        self,
        messages: list[AIMessage],
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        raise NotImplementedError


def require_api_key(provider_name: str, api_key: str) -> None:
    if not api_key:
        raise MissingAIProviderConfig(f"{provider_name} API key is not configured")


def first_text(value: Any, paths: list[list[str | int]]) -> str:
    for path in paths:
        cur = value
        try:
            for key in path:
                cur = cur[key]
            if isinstance(cur, str) and cur.strip():
                return cur.strip()
        except (KeyError, IndexError, TypeError):
            continue
    raise AIProviderError("AI provider returned an empty response")
