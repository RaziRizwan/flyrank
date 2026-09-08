"""
routers/delivery.py -- the two endpoints a stranger's browser calls: the config payload
(short-lived cache, changes whenever the owner edits the widget) and the widget.js loader
(long-lived, immutable cache -- but only at its versioned URL; the unversioned URL is
always fresh so a script tag that forgets ?v= still gets the latest loader).
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Response

import repository

router = APIRouter(tags=["delivery"])

BUNDLE_VERSION = "1"  # bump this -- and the URL that references it -- whenever widget.js's code changes
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


def error(status_code: int, message: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status_code, content={"error": message})


@router.get("/widgets/{widget_id}/config")
def get_widget_config(widget_id: int, response: Response):
    widget = repository.get_widget_public(widget_id)
    if widget is None:
        return error(404, f"widget {widget_id} not found")

    # Short-lived: the owner can edit a widget at any time, so this must not be cached
    # for long, but it also shouldn't hit the DB on every single page load either.
    response.headers["Cache-Control"] = "public, max-age=60"
    return {
        "id": widget["id"],
        "type": widget["type"],
        "title": widget["title"],
        "description": widget["description"],
        "fields": widget["fields"],
        "button_text": widget["button_text"],
        "display_options": widget["display_options"],
        "version": widget["version"],
    }


@router.get("/widget.js")
def get_widget_bundle(response: Response, v: Optional[str] = None):
    bundle_path = STATIC_DIR / "widget.js"
    content = bundle_path.read_text(encoding="utf-8")

    if v == BUNDLE_VERSION:
        # This exact URL will only ever serve this exact content -- safe to cache forever.
        cache_control = "public, max-age=31536000, immutable"
    else:
        # No version pinned (or a stale one): always revalidate, so an old embed snippet
        # that never updates its query string still gets today's loader.
        cache_control = "no-cache"

    return Response(
        content=content,
        media_type="application/javascript",
        headers={"Cache-Control": cache_control},
    )
