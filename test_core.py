"""Self-check for the non-network logic. Run: python test_core.py"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")

import brain
import db

now = datetime.now(timezone.utc)
db.add("discord", "1", now - timedelta(days=3), "Ana", "#events", "Venue booked", "https://d/1")
db.add("zoom", "u", (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z"), "h", "Sync", "Speakers confirmed")
db.add("discord", "1", now, "Ana", "#events", "dupe ignored", "https://d/1")
db.add("email", "m", (now - timedelta(days=20)).replace(tzinfo=None), "x", "Invoice", "old", "")

assert [i["text"] for i in db.since(now - timedelta(days=7))] == ["Venue booked", "Speakers confirmed"]
assert [i["text"] for i in db.since(now - timedelta(days=1))] == ["Speakers confirmed"]
assert db.latest("discord") == db.iso(now - timedelta(days=3))
assert db.latest("drive") is None

items = db.since(now - timedelta(days=7))
assert brain.link("Booked [1][2], speakers [1, 2] bogus [9]", items) == \
    "Booked [(1)](<https://d/1>)(2), speakers [(1)](<https://d/1>)(2) bogus (9)"

parts = brain.chunks("a" * 1500 + "\n" + "b" * 1500 + "\n" + "c" * 4500)
assert all(len(p) <= 2000 for p in parts) and "".join(parts).count("c") == 4500

brain.MAX_INPUT_CHARS = 200
kept, dropped = brain.fit([{"text": "x" * 50}] * 5)
assert len(kept) == 1 and dropped == 4

print("ok")
