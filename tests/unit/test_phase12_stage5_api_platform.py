"""
Unit tests for Phase 12 Stage 5: Enterprise API Platform & Architecture Addendum Enhancements.
"""

import pytest
import time
from akaal.api.facade import (
    Platform7Facade,
    APICapabilityRegistry,
    APILifecycleState,
    RBACRole,
    TraceContext,
    APIEndpointDescriptor,
)


def test_stage5_api_capability_registry():
    registry = APICapabilityRegistry()
    categories = registry.CATEGORIES

    assert len(categories) == 13
    assert "Migration" in categories
    assert "Workflow" in categories
    assert "Validation" in categories
    assert "Reporting" in categories
    assert "Security" in categories

    endpoints = registry.list_endpoints()
    assert len(endpoints) >= 13

    migration_eps = registry.get_endpoints_by_category("Migration")
    assert len(migration_eps) >= 2
    assert migration_eps[0].required_role == RBACRole.OPERATOR
    assert migration_eps[0].idempotent is True


def test_stage5_trace_context_propagation():
    trace = TraceContext()
    assert trace.request_id is not None
    assert trace.correlation_id is not None
    assert trace.trace_id is not None
    assert len(trace.span_id) == 16


def test_stage5_idempotency_processing():
    facade = Platform7Facade()

    payload = {"project_name": "IdempotentTest", "source": "pg"}
    key = "idem_key_9999"

    executed_count = 0

    def mock_handler():
        nonlocal executed_count
        executed_count += 1
        return {"status": "created", "project_id": "p_idem_1"}

    # First request -> executes handler
    res1 = facade.process_idempotent_request(key, payload, mock_handler)
    assert res1["status"] == "created"
    assert executed_count == 1

    # Duplicate request -> returns cached response without executing handler
    res2 = facade.process_idempotent_request(key, payload, mock_handler)
    assert res2["status"] == "created"
    assert res2.get("idempotent_replayed") is True
    assert executed_count == 1  # Handler was NOT executed again!


def test_stage5_idempotency_payload_mismatch_conflict():
    facade = Platform7Facade()
    key = "idem_key_conflict"

    def mock_handler():
        return {"status": "ok"}

    facade.process_idempotent_request(key, {"a": 1}, mock_handler)

    # Reusing same key with DIFFERENT payload raises ValueError conflict
    with pytest.raises(ValueError, match="Idempotency-Key reuse conflict"):
        facade.process_idempotent_request(key, {"a": 2}, mock_handler)


def test_stage5_maintenance_mode_toggle():
    facade = Platform7Facade()
    assert facade.is_maintenance_mode() is False

    facade.enable_maintenance_mode()
    assert facade.is_maintenance_mode() is True

    facade.disable_maintenance_mode()
    assert facade.is_maintenance_mode() is False


def test_stage5_optimistic_concurrency_etag():
    facade = Platform7Facade()
    data1 = {"id": 1, "version": 2}
    data2 = {"id": 1, "version": 3}

    etag1 = facade.compute_etag(data1)
    etag2 = facade.compute_etag(data2)

    assert etag1.startswith('"') and etag1.endswith('"')
    assert etag1 != etag2


def test_stage5_enterprise_webhook_trigger_and_signature():
    facade = Platform7Facade()
    wh = facade.register_enterprise_webhook(
        webhook_id="wh_001",
        target_url="https://example.com/webhooks",
        event_types=["MigrationCompleted"],
        secret="super_secret_key",
    )

    assert wh["webhook_id"] == "wh_001"

    event_payload = {"project_id": "p_100", "status": "SUCCESS"}
    deliv = facade.trigger_webhook("wh_001", "MigrationCompleted", event_payload)

    assert deliv["status"] == "DELIVERED"
    assert deliv["signature"].startswith("sha256=")


def test_stage5_facade_capabilities():
    facade = Platform7Facade()
    caps = facade.get_capabilities()

    assert "categories" in caps
    assert len(caps["categories"]) == 13
    assert "Idempotency" in caps["features"]
    assert caps["endpoint_count"] >= 13
