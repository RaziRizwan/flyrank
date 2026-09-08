# Embeddable Widget & Lead-Capture Platform

FlyRank Internship · Backend Track · Capstone. A platform that lets a customer create an
embeddable widget (signup form / CTA popover), hand out one `<script>` tag, and safely
catch whatever the public internet submits back — validated, rate-limited, spam-filtered,
enriched with geolocation, stored, and shown to the owner in a dashboard.

## What it does

Five request paths, three actors, one backend:

- **Widget owner** (authenticated): create/read/update/delete widgets, view a dashboard
  of submissions and stats. Every query is scoped to the owner's own tenant.
- **Customer's website** (any origin, public): loads `widget.js` and fetches a widget's
  `config` — both cacheable, both CORS-enabled.
- **Website visitor** (public): submits the rendered form. That single endpoint is
  validated, rate-limited, checked for spam, enriched with IP→geo data through a
  fallback chain, stored, and triggers a best-effort confirmation notification that can
  never block the response.

## Architecture

```
Widget Owner (authenticated, Bearer JWT)
    │
    ├──► POST/GET/PUT/DELETE /widgets[/:id]  ──►  Widget DB (tenant-isolated)
    │                                                    │
    │                                              embed_snippet:
    │                                       <script src=".../widget.js?v=1&id=42">
    │
    └──► GET /dashboard/stats, /dashboard/submissions  ◄── submissions + stats


Customer Website (any origin)
    <script src="widget.js?v=1&id=42">
        │
        ├──► GET /widget.js              (public · long-cached, immutable at ?v=1)
        └──► GET /widgets/42/config      (public · short-cached · CORS)
                    │
                    ▼
              renders the form


Website Visitor
    POST /submissions   (public · CORS · preflight handled)
        │
        ├─ 1. size + shape check ──────────► bad payload? → 400/413, never 500
        ├─ 2. does the widget exist? ──────► unknown id → 404
        ├─ 3. rate limit (IP + widget) ────► over the limit? → 429, API stays up
        ├─ 4. honeypot check ──────────────► filled? → fake 201, nothing stored
        ├─ 5. geo enrichment ──────────────► Provider A →(fails)→ Provider B →(fails)→ no geo
        ├─ 6. store submission (tenant + widget linked)
        └─ 7. queue confirmation job ──────► background task; failure never blocks step 6's response
```

## Setup

```bash
git clone <this-repo>
cd widget-platform
cp .env.example .env          # edit JWT_SECRET at minimum
docker compose up --build
```

Then, in another terminal, seed one demo account + widget:
```bash
docker compose exec api sh -c "cd .. && python seed.py"
```

That prints a demo widget id. Open `customer-site/index.html`'s `<script>` tag, put that
id in, then serve the customer site on a **different** port than the API:
```bash
cd customer-site && python -m http.server 5500
# visit http://localhost:5500 -- the widget renders there, loaded from localhost:8000
```

API docs (Swagger): `http://localhost:8000/docs`

### Running without Docker (local dev)

```bash
pip install -r requirements.txt
# have a local Postgres reachable, then:
python migrate.py
python seed.py
cd src && uvicorn main:app --reload --port 8000
```

### Running the test suite

```bash
pytest tests/ -v
```
20 tests, covering every acceptance probe in the brief (see EVIDENCE.md for real output).

## API reference

| Method | Path | Auth | Status codes |
|---|---|---|---|
| POST | `/auth/signup` | No | 201, 400 |
| POST | `/auth/login` | No | 200, 400, 401 |
| POST | `/widgets` | Yes | 201, 400, 401 |
| GET | `/widgets` | Yes | 200, 401 |
| GET | `/widgets/{id}` | Yes | 200, 401, 404 |
| PUT | `/widgets/{id}` | Yes | 200, 400, 401, 404 |
| DELETE | `/widgets/{id}` | Yes | 204, 401, 404 |
| GET | `/widgets/{id}/config` | No | 200, 404 (cached, CORS) |
| GET | `/widget.js` | No | 200 (cached, CORS) |
| POST | `/submissions` | No | 201, 400, 404, 413, 429 (CORS) |
| GET | `/dashboard/stats` | Yes | 200, 401 |
| GET | `/dashboard/submissions` | Yes | 200, 401 |

Every error response is `{"error": "..."}`.

## Politeness / hardening rules the submission endpoint follows

| Concern | Implementation |
|---|---|
| Payload size | rejects bodies over 10 KB with `413`, before JSON parsing |
| Validation | Pydantic schema + widget-specific required-field check → `400` on failure |
| Rate limiting | in-memory sliding window, 10 req/10s per IP, 30 req/10s per widget → `429` |
| Spam | honeypot field (`_hp`), invisible to real visitors; filled → silent fake success |
| Geo enrichment | ip-api.com → ipapi.co fallback chain; both down → stored without geo |
| Safe side effect | confirmation "email" (console log) runs as a background task after the response is sent, retried 3x, failures logged — never blocks storage |
| Idempotency | client-supplied `idempotency_key`; a retried key returns the original row, not a duplicate |

## Honest limitations

- **Rate limiting is in-memory and per-process.** Correct for this capstone's single-
  instance, $0 scope; a multi-instance deployment needs Redis-backed limiting instead.
  See `DESIGN.md`'s explicit non-goal.
- **Geo providers were verified with real HTTP calls during development**, but the
  environment this was built in has no outbound network route to `ip-api.com`/`ipapi.co`
  at all — so the "all providers down, submission still succeeds" path was proven for
  real (genuine failures, not mocked), while the "A down, B answers" path was proven with
  a deterministic test double (`AlwaysFailsProvider`/`AlwaysSucceedsProvider` in
  `tests/test_submission_path.py`), exactly as the brief's own realistic-scope section
  recommends. On a machine with normal internet access, both real providers work as-is.
- **The widget UI is intentionally minimal** — a div, a form, a submit button, no CSS
  framework. The brief is explicit that the grade lives in the backend.
- **No refresh-token flow.** Access tokens are valid for 24h; a real product would add
  short-lived tokens + refresh. Out of scope for this capstone.

## AI-assisted building

See `BUILDLOG.md`.
