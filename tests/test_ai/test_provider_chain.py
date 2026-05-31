import pytest

from src.ai.provider_chain import AIProviderChain, build_default_chain
from src.ai.providers.base import AIProvider, AIProviderError, MissingAIProviderConfig, RetriableAIProviderError


class FakeProvider(AIProvider):
    def __init__(
        self,
        name: str,
        response: str | None = None,
        error: Exception | None = None,
        errors: list[Exception] | None = None,
    ):
        self.name = name
        self.response = response
        self.error = error
        self.errors = list(errors or [])
        self.calls = 0

    def generate(self, messages, system="", temperature=0.2):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
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


def test_provider_chain_retries_retriable_error_before_success():
    provider = FakeProvider(
        "primary",
        response="retry success",
        errors=[RetriableAIProviderError("429"), RetriableAIProviderError("timeout")],
    )
    chain = AIProviderChain([provider], base_delay_seconds=0, jitter_seconds=0)

    assert chain.generate([{"role": "user", "content": "hi"}]) == "retry success"
    assert provider.calls == 3


def test_provider_chain_falls_back_after_retries_exhausted():
    primary = FakeProvider(
        "primary",
        errors=[
            RetriableAIProviderError("429"),
            RetriableAIProviderError("429"),
            RetriableAIProviderError("429"),
        ],
    )
    fallback = FakeProvider("fallback", response="fallback success")
    chain = AIProviderChain([primary, fallback], base_delay_seconds=0, jitter_seconds=0)

    assert chain.generate([{"role": "user", "content": "hi"}]) == "fallback success"
    assert primary.calls == 3
    assert fallback.calls == 1


def test_provider_chain_does_not_retry_non_retriable_error():
    primary = FakeProvider("primary", error=AIProviderError("401"))
    fallback = FakeProvider("fallback", response="fallback success")
    chain = AIProviderChain([primary, fallback], base_delay_seconds=0, jitter_seconds=0)

    assert chain.generate([{"role": "user", "content": "hi"}]) == "fallback success"
    assert primary.calls == 1


def test_provider_chain_requires_at_least_one_provider():
    with pytest.raises(MissingAIProviderConfig):
        AIProviderChain([])


def test_build_default_chain_uses_available_env_keys(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_ORDER", "gemini_flash,openai")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    chain = build_default_chain()

    assert [provider.name for provider in chain.providers] == ["gemini_flash"]
