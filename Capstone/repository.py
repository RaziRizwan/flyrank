"""
repository.py -- every SQL query in this project lives here. The golden rule from every
earlier assignment applies at capstone scale too: routers never write SQL, they call a
repository function. Every widget/submission function takes tenant_id as its first
argument and puts it in the WHERE clause -- that's the entire tenant-isolation mechanism,
enforced at the query, not the UI.
"""
from datetime import datetime, timezone
from typing import Optional

from database import get_connection


# --- tenants & users ------------------------------------------------------------------

def create_tenant_and_user(email: str, password_hash: str, tenant_name: str) -> dict:
    with get_connection() as conn:
        tenant = conn.execute(
            "INSERT INTO tenants (name) VALUES (%s) RETURNING id, name, created_at",
            (tenant_name,),
        ).fetchone()
        user = conn.execute(
            "INSERT INTO users (tenant_id, email, password_hash) VALUES (%s, %s, %s) "
            "RETURNING id, tenant_id, email, created_at",
            (tenant["id"], email, password_hash),
        ).fetchone()
        return user


def get_user_by_email(email: str) -> Optional[dict]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, tenant_id, email, password_hash, created_at FROM users WHERE email = %s",
            (email,),
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, tenant_id, email, created_at FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()


# --- widgets (every function takes tenant_id -- that IS the isolation) ----------------

def create_widget(tenant_id: int, type_: str, title: str, description: Optional[str],
                   fields: list, button_text: str, display_options: dict) -> dict:
    with get_connection() as conn:
        return conn.execute(
            """INSERT INTO widgets (tenant_id, type, title, description, fields, button_text, display_options)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id, tenant_id, type, title, description, fields, button_text,
                         display_options, version, created_at, updated_at""",
            (tenant_id, type_, title, description, _json(fields), button_text, _json(display_options)),
        ).fetchone()


def list_widgets(tenant_id: int) -> list[dict]:
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, tenant_id, type, title, description, fields, button_text,
                      display_options, version, created_at, updated_at
               FROM widgets WHERE tenant_id = %s ORDER BY id""",
            (tenant_id,),
        ).fetchall()


def get_widget(tenant_id: int, widget_id: int) -> Optional[dict]:
    """Scoped to tenant_id -- a widget belonging to another tenant simply does not match,
    same as if it didn't exist. This one query IS the isolation guarantee."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, tenant_id, type, title, description, fields, button_text,
                      display_options, version, created_at, updated_at
               FROM widgets WHERE id = %s AND tenant_id = %s""",
            (widget_id, tenant_id),
        ).fetchone()


def get_widget_public(widget_id: int) -> Optional[dict]:
    """The ONE place a widget is fetched without a tenant filter -- used only by the
    public config/delivery endpoints, which are allowed to serve any widget by design
    (that's the point of an embeddable widget). Everything else must go through
    get_widget() above."""
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, tenant_id, type, title, description, fields, button_text,
                      display_options, version, created_at, updated_at
               FROM widgets WHERE id = %s""",
            (widget_id,),
        ).fetchone()


def update_widget(tenant_id: int, widget_id: int, **fields) -> Optional[dict]:
    existing = get_widget(tenant_id, widget_id)
    if existing is None:
        return None
    updates = {
        "type": fields.get("type_", existing["type"]),
        "title": fields.get("title", existing["title"]),
        "description": fields.get("description", existing["description"]),
        "fields": _json(fields.get("fields", existing["fields"])),
        "button_text": fields.get("button_text", existing["button_text"]),
        "display_options": _json(fields.get("display_options", existing["display_options"])),
    }
    with get_connection() as conn:
        return conn.execute(
            """UPDATE widgets SET type=%s, title=%s, description=%s, fields=%s,
                      button_text=%s, display_options=%s, version = version + 1, updated_at = now()
               WHERE id = %s AND tenant_id = %s
               RETURNING id, tenant_id, type, title, description, fields, button_text,
                         display_options, version, created_at, updated_at""",
            (updates["type"], updates["title"], updates["description"], updates["fields"],
             updates["button_text"], updates["display_options"], widget_id, tenant_id),
        ).fetchone()


def delete_widget(tenant_id: int, widget_id: int) -> bool:
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM widgets WHERE id = %s AND tenant_id = %s RETURNING id",
            (widget_id, tenant_id),
        ).fetchone()
        return result is not None


# --- submissions ------------------------------------------------------------------------

def create_submission(widget_id: int, tenant_id: int, data: dict, ip_address: Optional[str],
                       geo_country: Optional[str], geo_city: Optional[str],
                       geo_provider: Optional[str], idempotency_key: Optional[str]) -> dict:
    with get_connection() as conn:
        if idempotency_key:
            existing = conn.execute(
                "SELECT id, widget_id, tenant_id, data, geo_country, geo_city, geo_provider, created_at "
                "FROM submissions WHERE widget_id = %s AND idempotency_key = %s",
                (widget_id, idempotency_key),
            ).fetchone()
            if existing:
                return {**existing, "deduplicated": True}
        row = conn.execute(
            """INSERT INTO submissions (widget_id, tenant_id, data, ip_address, geo_country,
                                        geo_city, geo_provider, idempotency_key)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id, widget_id, tenant_id, data, geo_country, geo_city, geo_provider, created_at""",
            (widget_id, tenant_id, _json(data), ip_address, geo_country, geo_city,
             geo_provider, idempotency_key),
        ).fetchone()
        return {**row, "deduplicated": False}


def list_submissions(tenant_id: int, widget_id: Optional[int] = None, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        if widget_id is not None:
            return conn.execute(
                """SELECT id, widget_id, tenant_id, data, geo_country, geo_city, geo_provider, created_at
                   FROM submissions WHERE tenant_id = %s AND widget_id = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (tenant_id, widget_id, limit),
            ).fetchall()
        return conn.execute(
            """SELECT id, widget_id, tenant_id, data, geo_country, geo_city, geo_provider, created_at
               FROM submissions WHERE tenant_id = %s ORDER BY created_at DESC LIMIT %s""",
            (tenant_id, limit),
        ).fetchall()


def submission_stats(tenant_id: int) -> dict:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM submissions WHERE tenant_id = %s", (tenant_id,)
        ).fetchone()["c"]
        per_widget = conn.execute(
            """SELECT w.id AS widget_id, w.title, COUNT(s.id) AS submission_count
               FROM widgets w LEFT JOIN submissions s ON s.widget_id = w.id AND s.tenant_id = %s
               WHERE w.tenant_id = %s GROUP BY w.id, w.title ORDER BY w.id""",
            (tenant_id, tenant_id),
        ).fetchall()
        geo_breakdown = conn.execute(
            """SELECT COALESCE(geo_country, 'unknown') AS country, COUNT(*) AS c
               FROM submissions WHERE tenant_id = %s GROUP BY geo_country ORDER BY c DESC""",
            (tenant_id,),
        ).fetchall()
        return {"total_submissions": total, "per_widget": per_widget, "geo_breakdown": geo_breakdown}


# --- background jobs (the safe side effect) --------------------------------------------

def enqueue_job(job_type: str, payload: dict) -> dict:
    with get_connection() as conn:
        return conn.execute(
            "INSERT INTO jobs (job_type, payload) VALUES (%s, %s) RETURNING id, job_type, payload, status",
            (job_type, _json(payload)),
        ).fetchone()


def mark_job_succeeded(job_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'succeeded', completed_at = now() WHERE id = %s",
            (job_id,),
        )


def mark_job_failed(job_id: int, error: str, attempts: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = 'failed', last_error = %s, attempts = %s, completed_at = now() WHERE id = %s",
            (error, attempts, job_id),
        )


def get_job(job_id: int) -> Optional[dict]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = %s", (job_id,)).fetchone()


# --- helpers -----------------------------------------------------------------------------

import json as _json_module

def _json(value):
    return _json_module.dumps(value)
