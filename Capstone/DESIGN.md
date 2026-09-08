# Design — Embeddable Widget & Lead-Capture Platform

One page, written before Phase 2, per the capstone's Phase 1 gate.

## Data model

**tenants** — `id, name, created_at`. A tenant is the isolation boundary; it exists as
its own row (not folded into `users`) so "tenant" and "user" stay conceptually distinct
even though this capstone creates one tenant per signup.

**users** — `id, tenant_id, email (unique), password_hash, created_at`. Belongs to
exactly one tenant.

**widgets** — `id, tenant_id, type, title, description, fields (jsonb), button_text,
display_options (jsonb), version, created_at, updated_at`. `fields` is a JSON array
(`[{name, label, required}]`) rather than a separate table — one or two widget types is
all the brief asks for, and a form's field list has no independent existence outside its
widget. `version` increments on every update, feeding the versioned-bundle cache story.

**submissions** — `id, widget_id, tenant_id (denormalized), data (jsonb), ip_address,
geo_country, geo_city, geo_provider, idempotency_key, created_at`. `tenant_id` is
duplicated from `widgets.tenant_id` on purpose: every submissions query filters on
`tenant_id` directly in its own `WHERE` clause, so a bug that forgets to join through
`widgets` can never leak another tenant's rows.

**jobs** — `id, job_type, payload (jsonb), status, attempts, last_error, created_at,
completed_at`. Backs the safe-side-effect background job (Phase 2).

**Indexes:** `tenant_id` on `users`, `widgets`, `submissions` (every isolation query hits
one); `widget_id` and `created_at` on `submissions` (dashboard queries); a unique index
on `(widget_id, idempotency_key)` where the key is non-null (idempotent retries).

## The embed flow

```
Owner creates a widget  →  API returns an embed_snippet: <script src=".../widget.js?v=1&id=42">
Customer pastes that tag on their own site (any origin)
  →  browser loads widget.js (long-cached, versioned URL)
  →  widget.js reads its own ?id=, fetches GET /widgets/42/config (short-cached, CORS)
  →  widget.js renders a form into the page from that config
Visitor fills the form, clicks submit
  →  widget.js POSTs to /submissions (CORS, validated, rate-limited, spam-checked,
      geo-enriched with a fallback chain, stored, side-effect queued)
```

## API contracts, one per actor

| Actor | Path | Auth | Notes |
|---|---|---|---|
| Owner | `POST/GET/PUT/DELETE /widgets[, /{id}]` | Bearer JWT | tenant-scoped by construction |
| Owner | `GET /dashboard/stats`, `/dashboard/submissions` | Bearer JWT | tenant-scoped |
| Customer's browser | `GET /widgets/{id}/config`, `GET /widget.js` | None | public, cached, CORS |
| Visitor's browser | `POST /submissions` | None | public, CORS, hardened |

Keeping these three paths in three separate router files (`widgets.py`, `delivery.py`,
`submissions.py`) is a design decision, not an accident — an authenticated route and a
public route should never be one accidental decorator away from swapping places.

## One explicit non-goal

**No production-grade rate limiting.** The limiter is in-memory, per-process
(`services/rate_limit.py`) — correct for a single instance, and exactly right for this
capstone's $0/local scope, but it would not survive a second process or a restart. A real
multi-instance deployment would move this state to Redis. Documented here rather than
quietly shipped as if it were production-ready.
