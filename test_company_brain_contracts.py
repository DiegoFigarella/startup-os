from datetime import datetime, timezone

import pytest

from company_brain.contracts import IngestItem


def item(**changes: object) -> IngestItem:
    values: dict[str, object] = {
        "source": "discord", "external_id": "123", "occurred_at": datetime(2026, 11, 14, tzinfo=timezone.utc),
        "author": "Maya", "place": "#partnerships", "text": "Sponsor call is Thursday.",
        "canonical_url": "https://discord.com/channels/1/2/123",
    }
    values.update(changes)
    return IngestItem(**values)


def test_same_source_record_and_revision_is_idempotent() -> None:
    assert item().idempotency_key == item().idempotency_key


def test_a_source_revision_is_a_distinct_record() -> None:
    assert item(revision="v1").idempotency_key != item(revision="v2").idempotency_key


@pytest.mark.parametrize("url", ["file:///secrets", "ftp://example.com/file"])
def test_non_web_source_url_is_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="HTTP"):
        item(canonical_url=url)
