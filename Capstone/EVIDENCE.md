# Evidence

One real, pasted proof per checkbox in the brief's Section 6 (Requirements), plus the
shared cross-cutting requirements. All output below is from actual runs against a real
PostgreSQL database (not simulated), captured while building this repo.

## Widget management

**☑ Authenticated CRUD endpoints for widgets; requests without valid auth are rejected.**
```
GET /widgets (no token) -> 401 {'detail': {'error': 'Access token required'}}
```

**☑ Multi-tenant isolation proven: tenant A cannot read or modify tenant B's widgets or submissions.**
```
GET /widgets/1 as tenant B -> 404 {'error': 'widget 1 not found'}
DELETE /widgets/1 as tenant B -> 404
GET /dashboard/submissions as tenant B (after tenant A has 1 submission) -> 200, []
```
See also: `tests/test_widgets_and_tenancy.py::test_tenant_cannot_read_another_tenants_widget`,
`::test_tenant_cannot_delete_another_tenants_widget`,
`::test_tenant_cannot_see_another_tenants_submissions_in_dashboard` — all passing.

**☑ Embed snippet generated per widget.**
```
POST /widgets -> 201
{
  "id": 1, "tenant_id": 1, "type": "signup_form", "title": "Join our newsletter",
  ...
  "embed_snippet": "<script src=\"http://localhost:8000/widget.js?v=1&id=1\"></script>"
}
```

## Widget delivery

**☑ Public config endpoint serves a small payload with correct HTTP cache headers.**
```
GET /widgets/1/config -> 200
Cache-Control: public, max-age=60
{"id": 1, "type": "signup_form", "title": "Join our newsletter", "fields": [...], ...}
```

**☑ Widget JavaScript is served as a versioned bundle (new version = new URL or cache-bust).**
```
GET /widget.js?v=1     -> Cache-Control: public, max-age=31536000, immutable
GET /widget.js (no v)  -> Cache-Control: no-cache
```
Real curl transcript (live uvicorn, not TestClient):
```
$ curl -s -i http://localhost:8000/widget.js?v=1
HTTP/1.1 200 OK
cache-control: public, max-age=31536000, immutable
content-type: application/javascript
```

**☑ The widget renders on a page served from a different origin than your API.**
`customer-site/index.html` is a static HTML file with no server-side code of its own,
containing exactly one `<script src="http://localhost:8000/widget.js?...">` tag. Serving
it with `python -m http.server 5500` puts it at `http://localhost:5500` while the API
runs at `http://localhost:8000` -- two different origins by the browser's own definition
(different port). `widget.js` derives its API base from `document.currentScript.src`
rather than a hardcoded domain, so it works from any origin without modification.
*(Honest note: this was verified by inspecting the real cross-origin HTTP calls the page
makes -- config fetch, CORS headers, script load -- not by driving an actual browser,
since no headless browser was available in the environment this was built in.)*

## Public submission API

**☑ Cross-origin submissions work: CORS headers correct, preflight (OPTIONS) handled.**
```
$ curl -s -i -X OPTIONS http://localhost:8000/submissions \
    -H "Origin: http://localhost:5500" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type"
HTTP/1.1 200 OK
access-control-allow-origin: *
access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
access-control-max-age: 600
access-control-allow-headers: content-type
```

**☑ All incoming input validated; malformed and oversized payloads rejected with appropriate 4xx codes and JSON errors.**
```
POST /submissions  (body: "{not valid json")        -> 400 {'error': 'invalid submission payload: ...'}
POST /submissions  (10KB+ payload)                   -> 413 {'error': 'payload too large -- max 10000 bytes'}
POST /submissions  (missing required field)          -> 400 {'error': "missing required field(s): email"}
POST /submissions  (unknown widget_id: 999999)       -> 404 {'error': 'widget 999999 not found'}
```
Never a 500 in any case above -- see `tests/test_submission_path.py` (5 tests covering this).

**☑ Valid submissions stored safely, linked to the right widget and tenant.**
```
POST /submissions {"widget_id": 1, "data": {"email": "visitor@example.com"}}
  -> 201 {'id': 1, 'widget_id': 1, 'created_at': '...', 'deduplicated': False}
GET /dashboard/submissions (as the widget's owner) -> includes id 1
```

## Abuse protection

**☑ Rate limiting per IP and/or per widget returns 429 under a burst -- and the API keeps serving legitimate traffic.**
```
15 rapid POST /submissions -> status codes:
[201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 429, 429, 429, 429, 429]
GET /health immediately after the burst -> 200
```

**☑ At least one spam-prevention technique demonstrably blocks a spam submission.**
```
POST /submissions {"widget_id": 1, "data": {"email": "bot@spam.com"}, "honeypot": "filled"}
  -> 201 {"status": "received"}      <- looks like success to the bot
Submission count before and after: identical -- nothing was actually stored.
```

## Enrichment & safe side effects

**☑ IP→geo enrichment uses a provider fallback chain: provider A down → provider B answers → submission enriched.**
```
enrich_with_fallback("1.2.3.4", [AlwaysFailsProvider(), AlwaysSucceedsProvider(country="Canada")])
  -> (GeoResult(country='Canada', city='Toronto'), 'mock-up')
```
(Deterministic test double, per the brief's own instruction to mock providers for this proof.)

**☑ All providers down → submission still succeeds (without geo). Degrade, never fail.**
```
enrich_with_fallback("1.2.3.4", [AlwaysFailsProvider(), AlwaysFailsProvider()]) -> (None, None)

-- and for real, not mocked: this sandbox's network has no route to ip-api.com/ipapi.co
-- at all, so every live submission below genuinely exercised the "every provider down"
-- path against real (failing) network calls:
POST /submissions {"widget_id": 1, "data": {"email": "geotest@example.com"}} -> 201
```

**☑ A failing confirmation email / webhook does not prevent the submission from being stored.**
```
POST /submissions (header: X-Test-Force-Notify-Failure: true)
  -> 201 {'id': 13, 'widget_id': 1, ...}          <- stored, success returned
[ALERT] notification job 13 failed after 3 attempts: simulated notification failure (for testing)
SELECT * FROM jobs WHERE id=13 -> status='failed', attempts=3, last_error='simulated notification failure...'
```

## Documentation

**☑ README with architecture diagram, setup instructions, and API documentation; the required files from Section 11 present.**
See `README.md` (architecture diagram, setup, API table) and this repo's root for
`capstone.yaml`, `EVIDENCE.md`, `BUILDLOG.md`, `.env.example`.

---

## Shared requirements (every capstone must show these)

**☑ Layered architecture -- data / logic / HTTP separated.**
`src/repository.py` (all SQL) / `src/services/*.py` (business logic: rate limiting, geo,
notifications) / `src/routers/*.py` (HTTP only -- no SQL, no business logic inline).

**☑ Validation at the boundary -- bad input → clean 4xx, never a 500.**
See the "malformed and oversized payloads" evidence above -- 5 dedicated tests, 0 failures,
0 unhandled exceptions.

**☑ ≥1 background job -- slow/bulk work off the request path, retries + failure alert.**
The confirmation-notification job (`services/notify.py` + the `jobs` table): queued via
`BackgroundTasks` (runs after the HTTP response is sent), retried up to 3 times, failure
logged with `[ALERT]` and recorded in `jobs.last_error`/`jobs.status`. See the safe-side-
effect evidence above for a real failed-job record.

**☑ Real persistence -- schema as migrations, right indexes, isolated tenants.**
Four numbered files in `migrations/`, applied by `migrate.py` (tracked in a
`schema_migrations` table, idempotent -- verified by running it twice). Indexes on every
`tenant_id` column plus `submissions.widget_id`/`created_at`, and a unique partial index
on `(widget_id, idempotency_key)`.

**☑ Idempotency where it matters -- the retried action happens once.**
```
POST /submissions {..., "idempotency_key": "retry-key-abc-123"}  -> 201, id=14, deduplicated=False
POST /submissions {..., "idempotency_key": "retry-key-abc-123"}  -> 201, id=14, deduplicated=True
```
Same `id` both times -- a retried submission never creates a second row.

**☑ Secrets clean -- env only, encrypted if stored, never logged.**
`DATABASE_URL`/`JWT_SECRET` are read exclusively via `os.environ` (`src/database.py`,
`src/auth.py`), loaded from `.env` (git-ignored, see `.gitignore`) via `python-dotenv`.
`.env.example` ships with placeholder values only. No secret value appears in any log
line printed by this application.

**Cost tracked, if AI is used -- per call, attributed, with a budget guard.**
Not applicable: this system makes no calls to any paid AI API at runtime (the geo
providers are free, keyless HTTP APIs, not AI services). No cost-tracking code exists
because there is no AI-API cost to track.
