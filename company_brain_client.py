"""Best-effort bridge from Startup OS sources to the Company Brain API."""
import json
import logging
import os
import urllib.request

log = logging.getLogger("startup-os.company-brain")


def ingest(source, external_id, occurred_at, author, place, text, canonical_url, revision="") -> None:
    """Mirror one normalized source item when Company Brain is configured."""
    base_url = os.getenv("COMPANY_BRAIN_URL", "").rstrip("/")
    api_key = os.getenv("COMPANY_BRAIN_API_KEY", "")
    scope = os.getenv("COMPANY_BRAIN_SCOPE", "")
    if not (base_url and api_key and scope):
        return

    payload = {
        "source": source,
        "external_id": str(external_id),
        "occurred_at": occurred_at.isoformat() if hasattr(occurred_at, "isoformat") else occurred_at,
        "author": author or "",
        "place": place or "",
        "text": text,
        "canonical_url": canonical_url or "",
        "scopes": [scope],
    }
    if revision:
        payload["revision"] = revision

    request = urllib.request.Request(
        f"{base_url}/v1/items",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Company-Brain-Key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except OSError:
        # shortcut: delivery is best-effort; add a durable outbox before relying on this as the only source of truth.
        log.exception("Company Brain mirror failed for %s item %s", source, external_id)


def ingest_discord(message) -> None:
    """Mirror a Discord message when Company Brain is configured."""
    text = message.clean_content
    if message.attachments:
        text += "\nAttachments: " + ", ".join(a.filename for a in message.attachments)
    ingest("discord", message.id, message.created_at, message.author.display_name,
           f"#{message.channel.name}", text, message.jump_url)
