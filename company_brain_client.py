"""Best-effort bridge from Startup OS sources to the Company Brain API."""
import json
import logging
import os
import urllib.request

log = logging.getLogger("startup-os.company-brain")


def ingest_discord(message) -> None:
    """Mirror a Discord message when Company Brain is configured."""
    base_url = os.getenv("COMPANY_BRAIN_URL", "").rstrip("/")
    api_key = os.getenv("COMPANY_BRAIN_API_KEY", "")
    scope = os.getenv("COMPANY_BRAIN_SCOPE", "")
    if not (base_url and api_key and scope):
        return

    payload = {
        "source": "discord",
        "external_id": str(message.id),
        "occurred_at": message.created_at.isoformat(),
        "author": message.author.display_name,
        "place": f"#{message.channel.name}",
        "text": message.clean_content,
        "canonical_url": message.jump_url,
        "scopes": [scope],
    }
    if message.attachments:
        payload["text"] += "\nAttachments: " + ", ".join(a.filename for a in message.attachments)

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
        log.exception("Company Brain mirror failed for Discord message %s", message.id)
