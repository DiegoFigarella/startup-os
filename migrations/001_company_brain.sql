CREATE SCHEMA IF NOT EXISTS company_brain;

CREATE TABLE IF NOT EXISTS company_brain.items (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  revision TEXT NOT NULL DEFAULT '',
  occurred_at TIMESTAMPTZ NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  author TEXT NOT NULL DEFAULT '',
  place TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL,
  canonical_url TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS company_brain_items_occurred_at_idx ON company_brain.items (occurred_at DESC);
CREATE INDEX IF NOT EXISTS company_brain_items_source_external_idx ON company_brain.items (source, external_id);

CREATE TABLE IF NOT EXISTS company_brain.item_scopes (
  item_id BIGINT NOT NULL REFERENCES company_brain.items(id) ON DELETE CASCADE,
  scope_id TEXT NOT NULL,
  PRIMARY KEY (item_id, scope_id)
);

CREATE INDEX IF NOT EXISTS company_brain_item_scopes_scope_idx ON company_brain.item_scopes (scope_id, item_id);

CREATE TABLE IF NOT EXISTS company_brain.source_cursors (
  source TEXT PRIMARY KEY,
  cursor TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
