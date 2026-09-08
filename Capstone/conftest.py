import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")
os.environ.setdefault("PUBLIC_BASE_URL", "http://localhost:8000")

# Derive a *_test database on the same host/credentials as whatever DATABASE_URL already
# points at (localhost in local dev, the `db` service name inside Docker Compose) --
# hardcoding "localhost" here would silently break inside a container.
_base_url = os.environ.get("DATABASE_URL", "postgres://postgres:dev@localhost:5432/widget_platform")
_parts = urlsplit(_base_url)
_test_db_name = _parts.path.lstrip("/") + "_test"
TEST_DATABASE_URL = urlunsplit((_parts.scheme, _parts.netloc, f"/{_test_db_name}", "", ""))
ADMIN_DATABASE_URL = urlunsplit((_parts.scheme, _parts.netloc, "/postgres", "", ""))

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
import psycopg
from fastapi.testclient import TestClient


def _ensure_test_database():
    """Creates the *_test database if it doesn't exist yet, then applies migrations."""
    with psycopg.connect(ADMIN_DATABASE_URL, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (_test_db_name,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{_test_db_name}"')

    import migrate
    migrate.run()


_ensure_test_database()

import database
import main as main_module


@pytest.fixture()
def client():
    with database.get_connection() as conn:
        conn.execute(
            "TRUNCATE submissions, jobs, widgets, users, tenants RESTART IDENTITY CASCADE"
        )
    from services.rate_limit import per_ip_limiter, per_widget_limiter
    per_ip_limiter.reset()
    per_widget_limiter.reset()
    return TestClient(main_module.app)


@pytest.fixture()
def tenant_a(client):
    client.post("/auth/signup", json={
        "email": "alice@acme.com", "password": "supersecret123", "company_name": "Acme",
    })
    r = client.post("/auth/login", json={"email": "alice@acme.com", "password": "supersecret123"})
    token = r.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture()
def tenant_b(client):
    client.post("/auth/signup", json={
        "email": "bob@other.com", "password": "differentpass1", "company_name": "OtherCo",
    })
    r = client.post("/auth/login", json={"email": "bob@other.com", "password": "differentpass1"})
    token = r.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture()
def widget(client, tenant_a):
    r = client.post("/widgets", json={
        "type": "signup_form", "title": "Join our newsletter",
        "fields": [{"name": "email", "label": "Email", "required": True}],
        "button_text": "Sign up",
    }, headers=tenant_a["headers"])
    return r.json()
