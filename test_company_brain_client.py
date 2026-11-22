import json
from datetime import datetime, timezone
from types import SimpleNamespace

import company_brain_client


def test_discord_message_is_mirrored(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass

    def open_request(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.data)
        return Response()

    monkeypatch.setenv("COMPANY_BRAIN_URL", "http://localhost:8088")
    monkeypatch.setenv("COMPANY_BRAIN_API_KEY", "local-key")
    monkeypatch.setenv("COMPANY_BRAIN_SCOPE", "org:utmist-startups")
    monkeypatch.setattr(company_brain_client.urllib.request, "urlopen", open_request)
    message = SimpleNamespace(
        id=123,
        created_at=datetime(2026, 11, 22, tzinfo=timezone.utc),
        author=SimpleNamespace(display_name="Maya"),
        channel=SimpleNamespace(name="partnerships"),
        clean_content="Sponsor confirmed.",
        jump_url="https://discord.com/channels/1/2/123",
        attachments=[],
    )

    company_brain_client.ingest_discord(message)

    assert captured["url"] == "http://localhost:8088/v1/items"
    assert captured["headers"]["X-company-brain-key"] == "local-key"
    assert captured["body"] == {
        "source": "discord", "external_id": "123", "occurred_at": "2026-11-22T00:00:00+00:00",
        "author": "Maya", "place": "#partnerships", "text": "Sponsor confirmed.",
        "canonical_url": "https://discord.com/channels/1/2/123", "scopes": ["org:utmist-startups"],
    }
