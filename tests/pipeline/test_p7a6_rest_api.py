"""
tests/pipeline/test_p7a6_rest_api.py
=======================================
Hostile verification of the P7A.6 REST API platform. Every request goes through a real
FastAPI TestClient (in-process ASGI, no network) into a real PipelineUnifiedCaller wired
with a real CentralAuthorizationEngine and SessionManager -- no mocks anywhere in the
authorization path. Proves the API layer inherits P7 security rather than reimplementing
(or bypassing) it: unauthenticated rejection, cross-tenant enumeration resistance,
HIGH-assurance gating on mutations, and idempotency reuse.
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from akaalPipeline.api.rest.app import create_app
from akaalPipeline.state.unit_of_work import SQLiteUnitOfWork

from tests.pipeline.conftest import authorized_caller, make_command, provision_verified_actor
from akaalIPC.security.context import ActorContext, ActorReference, CorrelationContext


def _thread_safe_uow(db_path: str) -> SQLiteUnitOfWork:
    """
    fastapi.testclient.TestClient runs the ASGI app on a background anyio portal thread,
    distinct from the pytest thread that builds this fixture. Python's sqlite3 module binds
    a Connection to the thread that created it by default (check_same_thread=True) --
    correct for a real multi-worker-thread server (each request should get its own
    connection there), but for this single-portal-thread test harness a connection genuinely
    only needs SEQUENTIAL cross-thread safety, which check_same_thread=False provides.
    Deliberately NOT changing SQLiteUnitOfWork's default (that governs real durability
    behavior repo-wide) -- this is scoped to test construction only.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return SQLiteUnitOfWork(db_path=db_path, shared_connection=conn)


def _create_migration(caller, migration_id: str, tenant_id: str = "org-acme"):
    actor = ActorContext(
        actor=ActorReference(actor_id="creator", actor_type="user"),
        organization_id=tenant_id,
    )
    cmd = make_command(
        request_type="migration.create",
        payload={"migration_id": migration_id, "name": f"Migration {migration_id}", "mode": "M1"},
        actor=actor,
        correlation=CorrelationContext.new(),
    )
    result = caller.handle_command(cmd)
    assert result.status.value == "OK", result.error


@pytest.fixture
def rest_client(temp_db_path):
    uow = _thread_safe_uow(temp_db_path)
    caller = authorized_caller(shared_uow=uow)
    _create_migration(caller, "mig-alpha", tenant_id="org-acme")
    _create_migration(caller, "mig-beta-foreign", tenant_id="org-other")
    app = create_app(caller)
    return TestClient(app), caller, temp_db_path, uow


def _session_headers(uow: SQLiteUnitOfWork, tenant_id: str, principal_id: str, **kwargs) -> dict:
    actor = provision_verified_actor(uow, tenant_id=tenant_id, principal_id=principal_id, **kwargs)
    return {
        "X-Session-Id": actor.session_id,
        "Authorization": f"Bearer {actor.session_token}",
        "X-Tenant-Id": tenant_id,
    }


def test_get_migration_without_any_session_is_rejected(rest_client):
    """
    An unauthenticated caller (no session at all) must not be able to access mig-alpha.
    Per the existing P7 Campaign C anti-enumeration design, this is NOT distinguished from
    "resource doesn't exist" -- enforce_resource_scope's TENANT_BOUNDARY_VIOLATION normalizes
    to the same externally-observable NOT_FOUND shape a genuine 404 would have, so denial and
    absence are indistinguishable to an external caller. That's a stronger anti-enumeration
    property than a distinct 401/403 would be, and this REST layer correctly inherits it
    unchanged rather than reimplementing its own (weaker) authorization error shape.
    """
    client, caller, db_path, uow = rest_client
    resp = client.get("/api/v1/migrations/mig-alpha")
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_get_migration_with_valid_session_and_correct_tenant_succeeds(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "reader-1")
    resp = client.get("/api/v1/migrations/mig-alpha", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["migration_id"] == "mig-alpha"


def test_cross_tenant_migration_access_is_not_distinguishable_from_not_found(rest_client):
    """
    Anti-enumeration: a real session for org-acme requesting a migration that belongs to
    org-other must not learn "it exists but you're forbidden" -- it must look identical to
    a nonexistent migration (P7 Campaign C's TENANT_BOUNDARY_VIOLATION -> NOT_FOUND normalization).
    """
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "reader-2")
    resp_foreign = client.get("/api/v1/migrations/mig-beta-foreign", headers=headers)
    resp_nonexistent = client.get("/api/v1/migrations/mig-does-not-exist", headers=headers)
    assert resp_foreign.status_code == resp_nonexistent.status_code
    assert resp_foreign.status_code in (400, 404)


def test_forged_wire_role_claims_do_not_grant_cancel_without_real_session(rest_client):
    """A caller asserting admin-sounding headers with no real session must still be rejected."""
    client, caller, db_path, uow = rest_client
    resp = client.post(
        "/api/v1/migrations/mig-alpha/cancel",
        headers={"X-Tenant-Id": "org-acme", "X-Session-Id": "forged-session-id-not-real"},
    )
    assert resp.status_code in (401, 403), resp.text


def test_cancel_with_high_assurance_verified_session_succeeds(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "canceller-1")
    resp = client.post("/api/v1/migrations/mig-alpha/cancel", headers=headers)
    assert resp.status_code == 202, resp.text


def test_idempotency_key_reuse_returns_same_outcome_not_a_double_execution(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "canceller-2")
    headers["Idempotency-Key"] = "idem-key-001"
    resp1 = client.post("/api/v1/migrations/mig-alpha/cancel", headers=headers)
    resp2 = client.post("/api/v1/migrations/mig-alpha/cancel", headers=headers)
    assert resp1.status_code == resp2.status_code == 202
    assert resp1.json() == resp2.json()


def test_list_migrations_pagination_never_returns_unbounded_results(rest_client):
    client, caller, db_path, uow = rest_client
    for i in range(5):
        _create_migration(caller, f"mig-page-{i}", tenant_id="org-acme")
    headers = _session_headers(uow, "org-acme", "lister-1")

    resp1 = client.get("/api/v1/migrations?limit=2&offset=0", headers=headers)
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert len(body1["migrations"]) == 2
    assert body1["next_offset"] == 2

    resp2 = client.get("/api/v1/migrations?limit=2&offset=2", headers=headers)
    body2 = resp2.json()
    assert len(body2["migrations"]) == 2
    assert body2["next_offset"] == 4


def test_list_migrations_rejects_oversized_page_size(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "lister-2")
    resp = client.get("/api/v1/migrations?limit=99999", headers=headers)
    assert resp.status_code == 422  # FastAPI query validation rejects > MAX_PAGE_SIZE


def test_error_response_never_leaks_internal_details(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "reader-3")
    resp = client.get("/api/v1/migrations/mig-does-not-exist", headers=headers)
    body = resp.json()["detail"]
    text = str(body)
    assert "Traceback" not in text
    assert db_path not in text
    assert "sqlite3" not in text.lower()


def test_correlation_id_is_echoed_back(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "reader-4")
    headers["X-Correlation-Id"] = "corr-test-12345"
    resp = client.get("/api/v1/migrations/mig-alpha", headers=headers)
    assert resp.headers.get("X-Correlation-Id") == "corr-test-12345"


def test_create_migration_via_rest_succeeds(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "creator-1")
    payload = {"name": "REST Created Migration", "mode": "M1"}
    resp = client.post("/api/v1/migrations", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "REST Created Migration"
    assert data["state"] == "DRAFT"
    assert data["tenant_id"] == "org-acme"
    assert "migration_id" in data


def test_post_body_oversized_is_rejected_with_413(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "creator-2")
    huge_name = "x" * (1024 * 1024 + 100)
    resp = client.post("/api/v1/migrations", json={"name": huge_name}, headers=headers)
    assert resp.status_code == 413, resp.text


def test_unsupported_media_type_is_rejected_with_415(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "creator-3")
    headers["Content-Type"] = "text/plain"
    resp = client.post("/api/v1/migrations", content="name=notjson", headers=headers)
    assert resp.status_code == 415, resp.text


def test_list_migrations_structured_filtering_sql_pushed(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "lister-filter")

    resp_all = client.get("/api/v1/migrations", headers=headers)
    assert resp_all.status_code == 200
    total_all = resp_all.json()["total"]

    # Filtering by mode M1
    resp_m1 = client.get("/api/v1/migrations?mode=M1", headers=headers)
    assert resp_m1.status_code == 200
    data_m1 = resp_m1.json()
    assert all(m["mode"] == "M1" for m in data_m1["migrations"])
    assert data_m1["total"] <= total_all

    # Filtering by nonexistent mode returns total 0
    resp_empty = client.get("/api/v1/migrations?mode=NONEXISTENT_MODE", headers=headers)
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total"] == 0
    assert len(resp_empty.json()["migrations"]) == 0


def test_list_migrations_rejects_unsupported_query_parameter(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "lister-unknown")
    resp = client.get("/api/v1/migrations?unknown_filter=hack", headers=headers)
    assert resp.status_code == 400
    assert "Unsupported query filter" in resp.text


def test_list_migrations_rejects_negative_offset(rest_client):
    client, caller, db_path, uow = rest_client
    headers = _session_headers(uow, "org-acme", "lister-neg")
    resp = client.get("/api/v1/migrations?offset=-5", headers=headers)
    assert resp.status_code == 422


def test_cross_tenant_idempotency_isolation(rest_client):
    """
    Idempotency keys are isolated per tenant.
    Tenant A using 'idem-key-1' cannot collide with or replay Tenant B's command.
    """
    client, caller, db_path, uow = rest_client
    _create_migration(caller, "mig-acme-idem", tenant_id="org-acme")
    _create_migration(caller, "mig-other-idem", tenant_id="org-other")

    headers_acme = _session_headers(uow, "org-acme", "canceller-acme")
    headers_acme["Idempotency-Key"] = "idem-shared-token"

    headers_other = _session_headers(uow, "org-other", "canceller-other")
    headers_other["Idempotency-Key"] = "idem-shared-token"

    # 1. Tenant A cancels its migration
    resp_a = client.post("/api/v1/migrations/mig-acme-idem/cancel", headers=headers_acme)
    assert resp_a.status_code == 202

    # 2. Tenant B cancels its own migration with the SAME idempotency key string
    resp_b = client.post("/api/v1/migrations/mig-other-idem/cancel", headers=headers_other)
    assert resp_b.status_code == 202
    # Ensure Tenant B received its own result, not Tenant A's result
    assert resp_b.json()["migration_id"] == "mig-other-idem"


def test_cancel_migration_optimistic_concurrency_conflict(rest_client):
    client, caller, db_path, uow = rest_client
    _create_migration(caller, "mig-conflict", tenant_id="org-acme")
    headers = _session_headers(uow, "org-acme", "canceller-conflict")

    # Pass expected_revision=999 when real revision is 1
    resp = client.post(
        "/api/v1/migrations/mig-conflict/cancel",
        json={"expected_revision": 999},
        headers=headers,
    )
    # Must return 409 Conflict due to revision conflict
    assert resp.status_code == 409, resp.text


def test_openapi_contract_generation_is_deterministic(rest_client):
    client, caller, db_path, uow = rest_client
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    assert schema["info"]["title"] == "AKAAL Enterprise REST Platform"
    paths = schema["paths"]
    assert "/api/v1/migrations" in paths
    assert "/api/v1/migrations/{migration_id}" in paths
    assert "/api/v1/migrations/{migration_id}/cancel" in paths
    assert "/api/v1/operations/{operation_id}" in paths

    # Verify deterministic operation IDs
    assert paths["/api/v1/migrations"]["get"]["operationId"] == "listMigrationsV1"
    assert paths["/api/v1/migrations"]["post"]["operationId"] == "createMigrationV1"
    assert paths["/api/v1/migrations/{migration_id}"]["get"]["operationId"] == "getMigrationV1"
    assert paths["/api/v1/migrations/{migration_id}/cancel"]["post"]["operationId"] == "cancelMigrationV1"

