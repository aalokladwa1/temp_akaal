"""Tests for Infrastructure Services, Policy Engine, Event Bus, and Distributed Coordinator."""

import pytest
from akaal.reliability.services.audit import ReliabilityAuditTrailService, ReliabilityObservabilityService, HealthScoringEngine
from akaal.reliability.policy.engine import ReliabilityPolicyEngine
from akaal.reliability.events.event_bus import ReliabilityEventBus, ReliabilityMetricsSubscriber
from akaal.reliability.events.events import ReliabilityEventType, ReliabilityEvent
from akaal.reliability.cache.reliability_cache import ReliabilityCache
from akaal.reliability.distributed.coordinator import DistributedReliabilityCoordinator


def test_audit_service():
    audit = ReliabilityAuditTrailService()
    entry = audit.log_entry("sess_001", "RETRY_ATTEMPT", "SYSTEM", "COMPLETED")
    assert entry["session_id"] == "sess_001"
    assert len(audit.get_audit_trail()) == 1


def test_health_scoring():
    hs = HealthScoringEngine()
    score = hs.compute_health_score(failure_rate=0.0, avg_latency_ms=50.0)
    assert score == 100.0


def test_policy_engine():
    pe = ReliabilityPolicyEngine()
    eval_res = pe.evaluate_reliability()
    assert eval_res["allowed"] is True
    assert eval_res["policy_decision"] == "APPROVED"


@pytest.mark.asyncio
async def test_event_bus():
    bus = ReliabilityEventBus()
    sub = ReliabilityMetricsSubscriber()
    bus.subscribe_all(sub.on_event)

    for et in list(ReliabilityEventType):
        await bus.publish(ReliabilityEvent(event_type=et, payload={"test": True}))

    assert len(sub.event_counts) == 15


def test_reliability_cache():
    cache = ReliabilityCache()
    cache.set("key1", "value1", ttl_sec=10.0)
    assert cache.get("key1") == "value1"
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_distributed_coordinator():
    coord = DistributedReliabilityCoordinator()
    leader = coord.elect_leader()
    assert leader is not None
    assert coord.get_leader() == leader
