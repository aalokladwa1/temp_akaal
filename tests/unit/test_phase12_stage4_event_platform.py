"""
Unit tests for Phase 12 Stage 4: Event & Messaging Platform.
"""

import pytest
import time
import hashlib
import json
from akaal.integration.composition_root import (
    GlobalEventRouter,
    EventEnvelope,
    DeliverySemantics,
    EventPriority,
    CircuitBreaker,
    CircuitBreakerState,
    EnterpriseLifecycleManager,
)
from akaal.orchestration.events.events import DomainEvent, WorkflowStarted


def test_stage4_domain_event_metadata_headers():
    event = WorkflowStarted(
        workflow_id="wf_123",
        job_id="job_456",
        initial_step="DISCOVERY",
        aggregate_id="proj_789",
        version="1.0",
        correlation_id="corr_abc",
        causation_id="cause_def",
        source="ManagerAgent",
        destination="ScoutAgent",
        delivery_mode="EXACTLY_ONCE",
        priority="P0_CRITICAL",
    )

    assert event.event_id is not None
    assert event.event_type == "WorkflowStarted"
    assert event.aggregate_id == "proj_789"
    assert event.version == "1.0"
    assert event.correlation_id == "corr_abc"
    assert event.causation_id == "cause_def"
    assert event.source == "ManagerAgent"
    assert event.destination == "ScoutAgent"
    assert event.delivery_mode == "EXACTLY_ONCE"
    assert event.priority == "P0_CRITICAL"


def test_stage4_global_event_router_delivery_and_persistence():
    router = GlobalEventRouter()

    payload = {"project_id": "p1", "action": "start"}
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    checksum = hashlib.sha256(payload_bytes).hexdigest()

    envelope = EventEnvelope(
        event_id="evt_001",
        event_type="TestEvent",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        aggregate_id="p1",
        version="1.0",
        checksum=checksum,
        payload=payload,
    )

    result = router.route_event(envelope)
    assert result["status"] == "DELIVERED"
    assert result["event_id"] == "evt_001"

    # Verify event store & replay
    replayed = router.replay_events("p1")
    assert len(replayed) == 1
    assert replayed[0].event_id == "evt_001"


def test_stage4_duplicate_event_suppression():
    router = GlobalEventRouter()

    envelope = EventEnvelope(
        event_id="evt_dup",
        event_type="DupEvent",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        aggregate_id="p1",
        payload={"k": "v"},
    )

    r1 = router.route_event(envelope)
    assert r1["status"] == "DELIVERED"

    r2 = router.route_event(envelope)
    assert r2["status"] == "DUPLICATE_SUPPRESSED"


def test_stage4_checksum_mismatch_dead_lettering():
    router = GlobalEventRouter()

    envelope = EventEnvelope(
        event_id="evt_corrupt",
        event_type="CorruptEvent",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        checksum="invalid_checksum_hash",
        payload={"data": "corrupted"},
    )

    result = router.route_event(envelope)
    assert result["status"] == "DEAD_LETTERED"
    assert result["reason"] == "CHECKSUM_MISMATCH"

    health = router.get_health_status()
    assert health["dead_letter_count"] == 1


def test_stage4_circuit_breaker_behavior():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    assert cb.state == CircuitBreakerState.CLOSED

    cb.record_failure()
    assert cb.state == CircuitBreakerState.CLOSED

    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert not cb.allow_execution()

    time.sleep(0.15)
    assert cb.allow_execution()
    assert cb.state == CircuitBreakerState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED


def test_stage4_bootstrap_context_integration():
    lifecycle = EnterpriseLifecycleManager()
    context = lifecycle.bootstrap()

    assert context.global_event_router is not None
    health = context.global_event_router.get_health_status()
    assert health["status"] == "HEALTHY"
