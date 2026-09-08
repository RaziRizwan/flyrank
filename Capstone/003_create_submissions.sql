-- 003_create_submissions.sql
-- tenant_id is denormalized here (also derivable via widget_id -> widgets.tenant_id) on
-- purpose: every submissions query filters on tenant_id directly, so a bug that forgets
-- to join through widgets can never leak another tenant's rows -- isolation enforced at
-- the query's first WHERE clause, not by a join being present.

CREATE TABLE IF NOT EXISTS submissions (
    id                 SERIAL PRIMARY KEY,
    widget_id          INTEGER NOT NULL REFERENCES widgets(id) ON DELETE CASCADE,
    tenant_id          INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    data               JSONB NOT NULL,           -- the validated form fields, as submitted
    ip_address         TEXT,
    geo_country        TEXT,
    geo_city           TEXT,
    geo_provider       TEXT,                     -- which provider answered, or NULL if all failed
    idempotency_key    TEXT,                     -- client-supplied; NULL means no dedup requested
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_submissions_tenant_id  ON submissions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_submissions_widget_id  ON submissions(widget_id);
CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);
-- Idempotency: the same (widget_id, idempotency_key) pair is only ever stored once,
-- when the client supplies a key -- so a retried submission after a dropped response
-- doesn't create a duplicate lead.
CREATE UNIQUE INDEX IF NOT EXISTS uq_submissions_widget_idem
    ON submissions(widget_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
