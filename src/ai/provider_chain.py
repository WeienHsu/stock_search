from __future__ import annotations

import os
from collections.abc import Iterable

from src.ai.providers.anthropic import AnthropicProvider
from src.ai.providers.base import AIMessage, AIProvider, AIProviderError, MissingAIProviderConfig
from src.ai.providers.gemini import GeminiProvider
from src.ai.providers.openai import OpenAIProvider


class AIProviderChain:
    def __init__(self, providers: Iterable[AIProvider]):
        self.providers = list(providers)
        if not self.providers:
            raise MissingAIProviderConfig("No AI providers are configured")

    def generate(
        self,
        messages: list[AIMessage],
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        errors: list[str] = []
        for provider in self.providers:
            try:
                text = provider.generate(messages, system=system, temperature=temperature).strip()
                if text:
                    return text
                raise AIProviderError("empty response")
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
        raise AIProviderError("All AI providers failed; " + " | ".join(errors))


def build_default_chain(user_id: str | None = None) -> AIProviderChain:
    providers: list[AIProvider] = []
    order = [
        item.strip()
        for item in os.getenv("AI_PROVIDER_ORDER", "anthropic_haiku,gemini_flash,openai,anthropic_sonnet").split(",")
        if item.strip()
    ]

    for item in order:
        provider = _build_provider(item, user_id)
        if provider is not None:
            providers.append(provider)

    return AIProviderChain(providers)


def _build_provider(name: str, user_id: str | None) -> AIProvider | None:
    if name == "anthropic_haiku":
        key = _secret_or_env(user_id, "anthropic_api_key", "ANTHROPIC_API_KEY")
        if not key:
            return None
        return AnthropicProvider(
            name="anthropic_haiku",
            api_key=key,
            model=os.getenv("ANTHROPIC_HAIKU_MODEL", "claude-3-5-haiku-latest"),
        )

    if name == "anthropic_sonnet":
        key = _secret_or_env(user_id, "anthropic_api_key", "ANTHROPIC_API_KEY")
        if not key:
            return None
        return AnthropicProvider(
            name="anthropic_sonnet",
            api_key=key,
            model=os.getenv("ANTHROPIC_SONNET_MODEL", "claude-3-5-sonnet-latest"),
        )

    if name == "gemini_flash":
        key = _secret_or_env(user_id, "gemini_api_key", "GEMINI_API_KEY")
        if not key:
            return None
        return GeminiProvider(
            name="gemini_flash",
            api_key=key,
            model=os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash"),
        )

    if name == "openai":
        key = _secret_or_env(user_id, "openai_api_key", "OPENAI_API_KEY")
        if not key:
            return None
        return OpenAIProvider(
            name="openai",
            api_key=key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

    return None


def _secret_or_env(user_id: str | None, secret_name: str, env_name: str) -> str:
    if user_id:
        try:
            from src.repositories.user_secrets_repo import get_secret

            value = get_secret(user_id, secret_name)
            if value:
                return value
        except Exception:
            pass
    return os.getenv(env_name, "")
