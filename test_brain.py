import asyncio
from types import SimpleNamespace

import brain


def test_catchup_uses_openai_and_links_citations(monkeypatch) -> None:
    captured = {}

    class Responses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text="Sponsor follow-up is due Thursday. [1]")

    class Client:
        responses = Responses()

    monkeypatch.setattr(brain, "AsyncOpenAI", Client)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    text = asyncio.run(brain.catchup([{
        "ts": "2026-11-22T12:00:00+00:00", "source": "discord", "place": "#partners",
        "author": "Maya", "text": "Follow up with sponsor by Thursday.", "url": "https://discord.com/channels/1/2/3",
    }], "Diego", "1 week"))

    assert captured["model"] == "test-model"
    assert captured["instructions"] == brain.SYSTEM
    assert "Reader: Diego" in captured["input"]
    assert text == "Sponsor follow-up is due Thursday. [(1)](<https://discord.com/channels/1/2/3>)"
