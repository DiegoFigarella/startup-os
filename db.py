"""Single SQLite table holding every ingested item, whatever its source."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

SCHEMA = """create table if not exists items(
    source text, ext_id text, ts text, author text, place text, text text, url text,
    primary key (source, ext_id))"""


def _conn():
    # ponytail: new connection per call keeps it thread-safe for asyncio.to_thread ingesters
    c = sqlite3.connect(os.getenv("DB_PATH", "brain.db"))
    c.execute(SCHEMA)
    return c


def iso(ts):
    """Normalize a datetime or ISO string to UTC 'YYYY-MM-DDTHH:MM:SS+00:00' so string compare == time compare."""
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")


def add(source, ext_id, ts, author, place, text, url=""):
    with closing(_conn()) as c, c:
        c.execute("insert or ignore into items values (?,?,?,?,?,?,?)",
                  (source, ext_id, iso(ts), author or "", place or "", text or "", url or ""))


def since(ts):
    with closing(_conn()) as c:
        c.row_factory = sqlite3.Row
        return [dict(r) for r in c.execute("select * from items where ts >= ? order by ts", (iso(ts),))]


def latest(source):
    """Newest timestamp stored for a source, used as the ingest cursor."""
    with closing(_conn()) as c:
        return c.execute("select max(ts) from items where source = ?", (source,)).fetchone()[0]
