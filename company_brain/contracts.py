from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class IngestItem:
    source: str
    external_id: str
    occurred_at: datetime
    author: str
    place: str
    text: str
    canonical_url: str
    revision: str = ""

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.external_id.strip():
            raise ValueError("source and external_id are required")
        if not self.text.strip():
            raise ValueError("text is required")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        if self.canonical_url and urlparse(self.canonical_url).scheme not in {"http", "https"}:
            raise ValueError("canonical_url must be an HTTP(S) URL")

    @property
    def idempotency_key(self) -> str:
        value = "\x1f".join((self.source, self.external_id, self.revision))
        return sha256(value.encode("utf-8")).hexdigest()

    @property
    def occurred_at_utc(self) -> datetime:
        return self.occurred_at.astimezone(timezone.utc)
