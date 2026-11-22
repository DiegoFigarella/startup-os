"""Turns a window of items into a cited catch-up summary."""
import os
import re

from openai import AsyncOpenAI

RANGES = {"1 day": 1, "3 days": 3, "1 week": 7, "2 weeks": 14, "1 month": 30}
MAX_INPUT_CHARS = 600_000  # ~150k tokens; newest items win when a window is bigger

SYSTEM = """You are Startup OS, the shared memory of the UTMIST Startups team (startup mentoring, \
outreach, event planning, partnerships, infra, marketing).

You get numbered updates from Discord, Zoom meeting summaries, Google Drive edits and invoice emails.
Write a catch-up for one director:
- Group by project or workstream, with a short bold heading for each.
- One line per point: decisions, tasks, deadlines, blockers, money. Skip chatter.
- End every line with its sources as [n], one bracket per number, e.g. [3][7]. Never invent numbers.
- Finish with a "Needs an owner" section for tasks nobody has claimed, if any.
- Call out anything that mentions or affects the reader by name.
- Plain Discord markdown, no tables. Be brief: this is read on a phone."""


def render(items):
    lines = []
    for n, it in enumerate(items, 1):
        lines.append(f"[{n}] {it['ts'][:16]} {it['source']} {it['place']} | {it['author']}: {it['text']}")
    return "\n".join(lines)


def fit(items):
    """Drop the oldest items until the prompt fits. Returns (kept, dropped_count)."""
    total, keep = 0, []
    for it in reversed(items):
        total += len(it["text"]) + 80
        if total > MAX_INPUT_CHARS:
            break
        keep.append(it)
    keep.reverse()
    return keep, len(items) - len(keep)


def link(summary, items):
    """Replace [n] / [n, m] citations with clickable Discord links (embeds suppressed)."""
    def one(n):
        n = int(n)
        url = items[n - 1]["url"] if 0 < n <= len(items) else ""
        return f"[({n})](<{url}>)" if url else f"({n})"
    return re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]",
                  lambda m: "".join(one(n) for n in re.split(r"\s*,\s*", m.group(1))), summary)


def chunks(text, limit=2000):
    """Split on line breaks into Discord-sized messages."""
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:  # a single giant line: hard-cut it
            out.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) > limit:
            out.append(cur)
            cur = ""
        cur += line
    return [c for c in out + [cur] if c.strip()]


async def catchup(items, reader, window):
    items, dropped = fit(items)
    client = AsyncOpenAI()
    response = await client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-6.2-astra"),
        max_output_tokens=16000,
        instructions=SYSTEM,
        input=f"Reader: {reader}\nWindow: last {window}\n\n{render(items)}",
    )
    text = link(response.output_text, items)
    if dropped:
        text += f"\n-# Skipped {dropped} oldest items to fit. Try a shorter range for full detail."
    return text
