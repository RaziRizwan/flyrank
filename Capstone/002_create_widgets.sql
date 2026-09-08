-- 002_create_widgets.sql
-- One or two widget types are all the brief asks for -- the type column is free text
-- rather than an enum table, since adding a third type later should never require a
-- migration.

CREATE TABLE IF NOT EXISTS widgets (
    id               SERIAL PRIMARY KEY,
    tenant_id        INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    type             TEXT NOT NULL,             -- 'signup_form' | 'cta_popover'
    title            TEXT NOT NULL,
    description      TEXT,
    fields           JSONB NOT NULL DEFAULT '[]',   -- e.g. [{"name":"email","label":"Email","required":true}]
    button_text      TEXT NOT NULL DEFAULT 'Submit',
    display_options  JSONB NOT NULL DEFAULT '{}',   -- e.g. {"theme":"light","position":"bottom-right"}
    version          INTEGER NOT NULL DEFAULT 1,     -- bumped on every update -> cache-busts the config
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_widgets_tenant_id ON widgets(tenant_id);
