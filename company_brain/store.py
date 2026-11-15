from __future__ import annotations

from collections.abc import Iterable

import psycopg

from .contracts import IngestItem


class CompanyBrainStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def ingest(self, item: IngestItem, scopes: Iterable[str]) -> bool:
        """Store one revision and its allowed QM scopes; duplicate delivery returns False."""
        with psycopg.connect(self._database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO company_brain.items
                  (idempotency_key, source, external_id, revision, occurred_at, author, place, text, canonical_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING id
                """,
                (item.idempotency_key, item.source, item.external_id, item.revision, item.occurred_at_utc,
                 item.author, item.place, item.text, item.canonical_url),
            )
            row = cur.fetchone()
            if row is None:
                return False
            for scope_id in set(scopes):
                cur.execute("INSERT INTO company_brain.item_scopes (item_id, scope_id) VALUES (%s, %s)", (row[0], scope_id))
            return True

    def recent(self, scope_id: str, limit: int = 50) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                """
                SELECT i.id, i.source, i.external_id, i.revision, i.occurred_at, i.author,
                       i.place, i.text, i.canonical_url
                FROM company_brain.items AS i
                JOIN company_brain.item_scopes AS s ON s.item_id = i.id
                WHERE s.scope_id = %s
                ORDER BY i.occurred_at DESC
                LIMIT %s
                """,
                (scope_id, limit),
            )
            return list(cur.fetchall())
