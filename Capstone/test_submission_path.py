import json
import time

import repository
import database
from services.geo import enrich_with_fallback, AlwaysFailsProvider, AlwaysSucceedsProvider


def test_probe_1_valid_submission_stored_and_visible_in_dashboard(client, tenant_a, widget):
    r = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "v@example.com"}},
                     headers={"Origin": "http://localhost:5500"})
    assert r.status_code == 201
    submission_id = r.json()["id"]

    r = client.get("/dashboard/submissions", headers=tenant_a["headers"])
    assert any(s["id"] == submission_id for s in r.json())


def test_probe_2_malformed_json_rejected_cleanly(client, widget):
    r = client.post("/submissions", content=b"{not valid", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_probe_2_oversized_payload_rejected(client, widget):
    huge = json.dumps({"widget_id": widget["id"], "data": {"email": "x" * 20000}})
    r = client.post("/submissions", content=huge, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_probe_2_missing_required_field_rejected(client, widget):
    r = client.post("/submissions", json={"widget_id": widget["id"], "data": {}})
    assert r.status_code == 400


def test_probe_2_unknown_widget_404_not_500(client):
    r = client.post("/submissions", json={"widget_id": 999999, "data": {"email": "a@b.com"}})
    assert r.status_code == 404


def test_probe_3_burst_triggers_429_then_recovers(client, widget):
    statuses = [
        client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": f"b{i}@x.com"}}).status_code
        for i in range(15)
    ]
    assert 429 in statuses
    assert 201 in statuses
    # the API itself is still up right after
    assert client.get("/health").status_code == 200


def test_probe_4_fallback_chain_uses_second_provider_when_first_fails():
    result, name = enrich_with_fallback("1.2.3.4", [AlwaysFailsProvider(), AlwaysSucceedsProvider(country="Canada")])
    assert result.country == "Canada"
    assert name == "mock-up"


def test_probe_4_all_providers_down_returns_none_not_an_exception():
    result, name = enrich_with_fallback("1.2.3.4", [AlwaysFailsProvider(), AlwaysFailsProvider()])
    assert result is None and name is None


def test_probe_4_submission_succeeds_even_with_zero_geo_providers_reachable(client, widget):
    # This sandbox's real network cannot reach ip-api.com/ipapi.co at all -- so this test
    # exercises the true "every provider down" path for real, not via a mock.
    r = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "geo@example.com"}})
    assert r.status_code == 201


def test_probe_5_side_effect_failure_does_not_block_submission(client, widget):
    r = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "se@example.com"}},
                     headers={"X-Test-Force-Notify-Failure": "true"})
    assert r.status_code == 201
    submission_id = r.json()["id"]

    time.sleep(1.0)
    with database.get_connection() as conn:
        job = conn.execute(
            "SELECT * FROM jobs WHERE payload->>'submission_id' = %s", (str(submission_id),)
        ).fetchone()
    assert job["status"] == "failed"
    assert job["attempts"] == 3


def test_probe_6_honeypot_silently_drops_without_storing(client, tenant_a, widget):
    before = len(repository.list_submissions(tenant_id=tenant_a_id(client, tenant_a), widget_id=widget["id"]))
    r = client.post("/submissions", json={
        "widget_id": widget["id"], "data": {"email": "bot@spam.com"}, "honeypot": "filled",
    })
    assert r.status_code == 201  # looks like success to the bot
    after = len(repository.list_submissions(tenant_id=tenant_a_id(client, tenant_a), widget_id=widget["id"]))
    assert after == before


def test_idempotency_key_prevents_duplicate_storage(client, widget):
    key = "retry-key-xyz"
    r1 = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "i@x.com"}, "idempotency_key": key})
    r2 = client.post("/submissions", json={"widget_id": widget["id"], "data": {"email": "i@x.com"}, "idempotency_key": key})
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["deduplicated"] is True


def test_cors_preflight_handled(client):
    r = client.options("/submissions", headers={
        "Origin": "http://localhost:5500",
        "Access-Control-Request-Method": "POST",
    })
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") is not None


def tenant_a_id(client, tenant_a) -> int:
    r = client.get("/widgets", headers=tenant_a["headers"])
    return r.json()[0]["tenant_id"]
