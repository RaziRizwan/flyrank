def test_unauthenticated_request_rejected(client):
    r = client.get("/widgets")
    assert r.status_code == 401


def test_signup_and_login(client):
    r = client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})
    assert r.status_code == 201
    r = client.post("/auth/login", json={"email": "new@example.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_rejected(client):
    client.post("/auth/signup", json={"email": "x@example.com", "password": "password123"})
    r = client.post("/auth/login", json={"email": "x@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_create_widget_returns_embed_snippet(client, tenant_a):
    r = client.post("/widgets", json={"type": "signup_form", "title": "Test"}, headers=tenant_a["headers"])
    assert r.status_code == 201
    assert "embed_snippet" in r.json()
    assert "<script" in r.json()["embed_snippet"]


def test_tenant_cannot_read_another_tenants_widget(client, tenant_a, tenant_b, widget):
    r = client.get(f"/widgets/{widget['id']}", headers=tenant_b["headers"])
    assert r.status_code == 404  # not 403 -- indistinguishable from "doesn't exist"


def test_tenant_cannot_delete_another_tenants_widget(client, tenant_a, tenant_b, widget):
    r = client.delete(f"/widgets/{widget['id']}", headers=tenant_b["headers"])
    assert r.status_code == 404
    # and it's still there for the owner
    r = client.get(f"/widgets/{widget['id']}", headers=tenant_a["headers"])
    assert r.status_code == 200


def test_tenant_cannot_see_another_tenants_submissions_in_dashboard(client, tenant_a, tenant_b, widget):
    client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "x@example.com"}})
    r = client.get("/dashboard/submissions", headers=tenant_b["headers"])
    assert r.status_code == 200
    assert r.json() == []  # tenant B sees nothing, even though tenant A has a submission
