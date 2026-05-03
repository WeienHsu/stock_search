import json

from src.notifications import line_messaging
from src.notifications.line_messaging import LineMessagingChannel


class ResponseStub:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_line_messaging_uses_push_api(monkeypatch):
    requests = []
    monkeypatch.setattr(
        line_messaging,
        "get_settings",
        lambda user_id: {"line_enabled": True, "line_user_id": "U123"},
    )
    monkeypatch.setattr(line_messaging, "get_secret", lambda user_id, name: "token")

    def fake_urlopen(request, timeout=20):
        requests.append(request)
        return ResponseStub()

    monkeypatch.setattr(line_messaging, "urlopen", fake_urlopen)

    assert LineMessagingChannel().send("user-1", "主旨", "內容") is True

    request = requests[0]
    assert request.full_url == "https://api.line.me/v2/bot/message/push"
    assert request.headers["Authorization"] == "Bearer token"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["to"] == "U123"
    assert payload["messages"][0]["type"] == "text"
    assert "主旨" in payload["messages"][0]["text"]
