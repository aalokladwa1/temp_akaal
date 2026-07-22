"""
Integration tests for FastAPI REST API endpoints (/api/v1).
"""

from fastapi.testclient import TestClient
from akaal.api.rest.app import create_app

app = create_app()
client = TestClient(app)

HEADERS = {"X-API-Key": "akaal_live_test_key_123"}


def test_health_and_readiness_endpoints():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"

    response = client.get("/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "READY"

    response = client.get("/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "ALIVE"


def test_openapi_spec():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "/api/v1/jobs" in data["paths"]


def test_submit_job_rest_flow():
    payload = {"job_type": "copy_table", "payload": {"source": "db_a", "target": "db_b"}}
    response = client.post("/api/v1/jobs", json=payload, headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "QUEUED"

    # Query Status
    job_id = data["job_id"]
    response = client.get(f"/api/v1/jobs/{job_id}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["job_id"] == job_id


def test_idempotency_headers_integration():
    headers = {**HEADERS, "X-Idempotency-Key": "idem-key-test-100"}
    payload = {"job_type": "unique_job", "payload": {}}

    # First Request
    r1 = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert r1.status_code == 200
    job_id_1 = r1.json()["job_id"]

    # Replayed Request with same Idempotency Key
    r2 = client.post("/api/v1/jobs", json=payload, headers=headers)
    assert r2.status_code == 200
    assert r2.headers.get("X-Cache") == "HIT-IDEMPOTENT"
    assert r2.json()["job_id"] == job_id_1
