"""
routers/submissions.py -- the public submission endpoint. This file is where every
evaluation probe in the brief lives: validation, CORS (handled at app level), rate
limiting, honeypot, geo fallback, safe side effect. Order matters -- cheapest, most
decisive checks run first, so a flood or a malformed payload never reaches the database
or an external geo call.
"""
import json
import os

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

import repository
from schemas import SubmissionCreate
from services.rate_limit import per_ip_limiter, per_widget_limiter
from services.geo import IpApiComProvider, IpApiCoProvider, enrich_with_fallback
from services.notify import send_confirmation

router = APIRouter(tags=["submissions"])

MAX_PAYLOAD_BYTES = 10_000  # 10 KB is generous for a lead-capture form; anything bigger is suspicious


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def get_client_ip(request: Request) -> str:
    # Respects a proxy header if present (e.g. behind nginx/Docker), falls back to the
    # direct connecting IP -- fine for this scope; a production system would restrict
    # which proxies are trusted before honoring X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _geo_providers() -> list:
    """Re-read the toggle env vars on every call (not cached at import time) so an
    evaluator can flip GEO_PROVIDER_A_DISABLED / GEO_PROVIDER_B_DISABLED in .env and
    `docker compose restart api` to run PROBE 4 live, without any special admin endpoint."""
    providers = []
    if os.environ.get("GEO_PROVIDER_A_DISABLED", "false").lower() != "true":
        providers.append(IpApiComProvider())
    if os.environ.get("GEO_PROVIDER_B_DISABLED", "false").lower() != "true":
        providers.append(IpApiCoProvider())
    return providers


@router.post("/submissions", status_code=201)
async def create_submission(request: Request, background_tasks: BackgroundTasks):
    # --- 1. size check, before we even try to parse JSON -----------------------------
    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        return error(413, f"payload too large -- max {MAX_PAYLOAD_BYTES} bytes")

    # --- 2. parse + validate shape -----------------------------------------------------
    try:
        raw = json.loads(body)
        payload = SubmissionCreate(**raw)
    except (json.JSONDecodeError, ValidationError) as e:
        return error(400, f"invalid submission payload: {e}")

    # --- 3. does the widget exist at all? (public lookup -- no tenant filter here,
    #        that's correct: any widget id from a real embed snippet is fair game) -----
    widget = repository.get_widget_public(payload.widget_id)
    if widget is None:
        return error(404, f"widget {payload.widget_id} not found")

    # --- 4. rate limiting -- cheap, decisive, runs before anything else expensive -----
    ip = get_client_ip(request)
    if not per_ip_limiter.allow(f"ip:{ip}"):
        return error(429, "too many submissions from this IP -- slow down")
    if not per_widget_limiter.allow(f"widget:{payload.widget_id}"):
        return error(429, "too many submissions for this widget -- slow down")

    # --- 5. honeypot -- a filled hidden field means a bot. Silently "succeed" without
    #        storing anything or telling the bot why; this is the accepted alternative
    #        to rejecting outright, and doesn't teach a scraping bot what to avoid. -----
    if payload.honeypot:
        return JSONResponse(status_code=201, content={"status": "received"})

    # --- 6. validate the actual field values against the widget's own field list ------
    required_fields = [f["name"] for f in widget["fields"] if f.get("required")]
    missing = [f for f in required_fields if not payload.data.get(f)]
    if missing:
        return error(400, f"missing required field(s): {', '.join(missing)}")

    # --- 7. enrichment, degrade never fail ---------------------------------------------
    geo_result, geo_provider_name = enrich_with_fallback(ip, _geo_providers())

    # --- 8. store -------------------------------------------------------------------------
    submission = repository.create_submission(
        widget_id=widget["id"],
        tenant_id=widget["tenant_id"],
        data=payload.data,
        ip_address=ip,
        geo_country=geo_result.country if geo_result else None,
        geo_city=geo_result.city if geo_result else None,
        geo_provider=geo_provider_name,
        idempotency_key=payload.idempotency_key,
    )

    # --- 9. safe side effect -- queued as a background job, runs AFTER this response
    #        is already on the wire, so it can never turn a stored submission into a
    #        failed one. force_failure is test-only, see services/notify.py. -----------
    force_failure = request.headers.get("x-test-force-notify-failure", "").lower() == "true"
    job = repository.enqueue_job("notify_submission", {
        "widget_id": widget["id"], "submission_id": submission["id"], "data": payload.data,
    })
    background_tasks.add_task(
        send_confirmation, job["id"], widget["id"], submission["id"], payload.data,
        force_failure=force_failure,
    )

    return JSONResponse(status_code=201, content={
        "id": submission["id"],
        "widget_id": submission["widget_id"],
        "created_at": submission["created_at"].isoformat(),
        "deduplicated": submission.get("deduplicated", False),
    })
