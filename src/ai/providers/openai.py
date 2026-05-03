from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from src.ai.providers.base import AIMessage, AIProvider, AIProviderError, first_text, require_api_key


@dataclass
class OpenAIProvider(AIProvider):
    api_key: str
    model: str
    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"

    def generate(
        self,
        messages: list[AIMessage],
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        require_api_key(self.name, self.api_key)
        payload_messages: list[dict[str, str]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend({"role": msg["role"], "content": msg["content"]} for msg in messages)

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
        }
        data = _post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            self.name,
        )
        return first_text(data, [["choices", 0, "message", "content"]])


def _post_json(url: str, payload: dict, headers: dict[str, str], provider_name: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AIProviderError(f"{provider_name} API error {exc.code}: {detail[:300]}") from exc
    except Exception as exc:
        raise AIProviderError(f"{provider_name} request failed: {exc}") from exc
