# Build log — AI usage

This entire repository was built by Claude (Anthropic), working directly in a sandboxed
environment with a real PostgreSQL instance, executing and testing code rather than only
generating it. This log is an honest account of that process, including what broke along
the way -- not just a description of the finished result.

## Where AI helped

- Generated the full layered architecture (`repository.py` / `services/` / `routers/`)
  from the brief's requirements, and kept it to that layering consistently across five
  routers and three services.
- Wrote and ran a 20-test pytest suite covering every one of the brief's six acceptance
  probes, plus tenant isolation and idempotency, against a real database.
- Iteratively found and fixed real bugs by actually executing the code (see below), not
  by inspection alone.

## Where it got things wrong, and what changed

**1. `passlib` + `bcrypt` incompatibility.** The first pass used `passlib.CryptContext`
for password hashing, following a common pattern from training data. Running it for real
immediately raised an error inside passlib's version-detection code -- passlib is
unmaintained and breaks against `bcrypt>=4.1`. Fixed by dropping passlib entirely and
calling `bcrypt.hashpw`/`bcrypt.checkpw` directly, which is simpler anyway. This was only
caught because the code was actually run, not just read.

**2. `datetime` objects breaking `JSONResponse`.** `POST /widgets` initially crashed with
`TypeError: Object of type datetime is not JSON serializable`. FastAPI auto-encodes plain
dict/list return values through `jsonable_encoder`, but an explicitly-constructed
`JSONResponse(...)` (used here to set a custom `201` status) bypasses that step and calls
plain `json.dumps` instead -- a distinction easy to get wrong and easy to miss without
running the endpoint. Fixed by wrapping the content in `jsonable_encoder(...)` at every
explicit `JSONResponse` call site that carries a datetime field.

**3. A hardcoded `localhost` in the test suite that would have silently broken inside
Docker.** `tests/conftest.py` first hardcoded `postgres://postgres:dev@localhost:5432/...`
for its test-database setup. That works in local dev, where Postgres is on `localhost`,
but Docker Compose reaches the database container by service name (`db`), not
`localhost` -- so `capstone.yaml`'s `test:` command would have failed (or silently pointed
at the wrong database) the moment someone actually ran it inside the container. Fixed by
deriving the test database's connection details from whatever `DATABASE_URL` is already
set to, rather than assuming a host.

**4. Missing `email-validator` dependency.** Pydantic's `EmailStr` type raised an
`ImportError` on the first real request, not at import time -- it lazy-imports its
validator. Caught immediately by running an actual signup request rather than only
checking that the code parsed.

## What this suggests about using AI to build backend systems

Every bug listed above was invisible from reading the code -- each one only surfaced by
actually running it against a real database and real HTTP requests. The value Claude
added here wasn't "generate code that looks right"; it was generating code, running it,
watching it fail, and fixing the actual failure. A description of this system that only
showed working final code, with no acknowledgment of the passlib crash or the datetime
bug, would be a less honest artifact than this one.

## One AI rematch (per the brief's bonus stage)

Not attempted in this build -- doing so meaningfully requires a second, independent
implementation generated from a fresh prompt and compared against this one, which is a
substantial undertaking on top of an already large capstone. Recommended as a genuine
next step for whoever owns this repo, not simulated here for the sake of ticking the box.
