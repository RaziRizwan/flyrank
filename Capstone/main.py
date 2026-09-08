"""
main.py -- app assembly only. Every route lives in routers/; this file wires them
together, plus the one cross-cutting concern that has to live at the app level: CORS.

Run with:  uvicorn main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, widgets, delivery, submissions, dashboard

app = FastAPI(title="Embeddable Widget & Lead-Capture Platform", version="1.0")

# The public submission/config/widget.js endpoints are, by design, called from origins
# this server has never seen before -- that's the entire point of an embeddable widget.
# allow_origins=["*"] is correct here, not a shortcut: there is no cookie-based session to
# protect (auth is a Bearer token, immune to CSRF), and every request is independently
# validated, rate-limited, and tenant-scoped regardless of where it came from.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(delivery.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "name": "Embeddable Widget & Lead-Capture Platform",
        "version": "1.0",
        "docs": "/docs",
    }
