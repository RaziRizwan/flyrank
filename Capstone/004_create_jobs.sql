-- 004_create_jobs.sql
-- The confirmation-email/webhook side effect runs as a background job: queued after the
-- submission is already stored, retried on failure, and logged if it never succeeds --
-- so a dead mail server can never take down the public submission endpoint.

CREATE TABLE IF NOT EXISTS jobs (
    id            SERIAL PRIMARY KEY,
    job_type      TEXT NOT NULL,                 -- 'notify_submission'
    payload       JSONB NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending', -- pending | succeeded | failed
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
