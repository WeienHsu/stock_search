import pytest

from src.ai.provider_chain import AIProviderChain, build_default_chain
from src.ai.providers.base import AIProvider, AIProviderError, MissingAIProviderConfig


class FakeProvider(AIProvider):
    def __init__(self, name: str, response: str | None = None, error: Exception | None = None):
        self.name = name
        self.response = response
        self.error = error
        self.calls = 0

    def generate(self, messages, system="", temperature=0.2):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response or ""


def test_provider_chain_falls_back_after_primary_failure():
    primary = FakeProvider("primary", error=AIProviderError("boom"))
    fallback = FakeProvider("fallback", response="中文解讀")

    chain = AIProviderChain([primary, fallback])

    assert chain.generate([{"role": "user", "content": "hi"}]) == "中文解讀"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_provider_chain_reports_all_failures():
    chain = AIProviderChain([
        FakeProvider("a", error=AIProviderError("first")),
        FakeProvider("b", error=AIProviderError("second")),
    ])

    with pytest.raises(AIProviderError) as exc:
        chain.generate([{"role": "user", "content": "hi"}])

    assert "a: first" in str(exc.value)
    assert "b: second" in str(exc.value)


def test_provider_chain_requires_at_least_one_provider():
    with pytest.raises(MissingAIProviderConfig):
        AIProviderChain([])


def test_build_default_chain_uses_available_env_keys(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "gemini_flash,openai")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    chain = build_default_chain()

    assert [provider.name for provider in chain.providers] == ["gemini_flash"]
