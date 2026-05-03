from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from src.ai.providers.base import AIMessage, AIProvider, AIProviderError, first_text, require_api_key


@dataclass
class GeminiProvider(AIProvider):
    api_key: str
    model: str
    name: str = "gemini"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate(
        self,
        messages: list[AIMessage],
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        require_api_key(self.name, self.api_key)
        text = _messages_to_text(messages, system)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": temperature},
        }
        url = (
            f"{self.base_url.rstrip('/')}/{urllib.parse.quote(self.model)}:generateContent"
            f"?key={urllib.parse.quote(self.api_key)}"
        )
        data = _post_json(url, payload, {"Content-Type": "application/json"}, self.name)
        return first_text(data, [["candidates", 0, "content", "parts", 0, "text"]])


def _messages_to_text(messages: list[AIMessage], system: str) -> str:
    parts: list[str] = []
    if system:
        parts.append(f"System:\n{system}")
    for msg in messages:
        parts.append(f"{msg['role'].title()}:\n{msg['content']}")
    return "\n\n".join(parts)


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
