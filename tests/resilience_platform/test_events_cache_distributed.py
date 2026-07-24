"""Tests: Resilience Platform — Event Bus, Cache, Distributed Coordinator, Audit Service."""

import pytest
from akaal.resilience_eng.events.event_bus import ResilienceEventBus, ResilienceEvent, ResilienceEventType
from akaal.resilience_eng.events.publishers import ResilienceEventPublisher
from akaal.resilience_eng.cache.resilience_cache import ResilienceCache
from akaal.resilience_eng.distributed.coordinator import DistributedExperimentCoordinator
from akaal.resilience_eng.services.audit import ResilienceAuditTrailService, ResilienceObservabilityService, ResilienceHealthService


class TestResilienceEventBus:
    def test_publish_and_subscribe(self):
        bus = ResilienceEventBus()
        received = []
        bus.subscribe(ResilienceEventType.EXPERIMENT_SUBMITTED, lambda e: received.append(e))
        event = ResilienceEvent(event_type=ResilienceEventType.EXPERIMENT_SUBMITTED, experiment_id="exp_001")
        bus.publish(event)
        assert len(received) == 1
        assert received[0].experiment_id == "exp_001"

    def test_publish_all_20_event_types(self):
        bus = ResilienceEventBus()
        for et in ResilienceEventType:
            bus.publish(ResilienceEvent(event_type=et, experiment_id="exp_001"))
        assert bus.published_count() == 20

    def test_publisher_convenience_method(self):
        bus = ResilienceEventBus()
        pub = ResilienceEventPublisher(bus)
        pub.publish(ResilienceEventType.EXPERIMENT_APPROVED, "exp_001", {"reason": "All checks passed"})
        assert bus.published_count() == 1


class TestResilienceCache:
    def test_set_and_get(self):
        cache = ResilienceCache()
        cache.set("exp_001_score", 98.5)
        assert cache.get("exp_001_score") == 98.5

    def test_invalidate(self):
        cache = ResilienceCache()
        cache.set("key", "value")
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_miss_returns_none(self):
        cache = ResilienceCache()
        assert cache.get("nonexistent_key") is None

    def test_size_tracking(self):
        cache = ResilienceCache()
        for i in range(5):
            cache.set(f"key_{i}", i)
        assert cache.size() == 5


class TestDistributedExperimentCoordinator:
    def test_acquire_and_release_lease(self):
        coord = DistributedExperimentCoordinator()
        lease = coord.acquire_lease("worker_01", "exp_001")
        assert lease.is_active is True
        status = coord.get_coordinator_status()
        assert status["active_leases"] == 1
        coord.release_lease(lease.lease_id)
        status2 = coord.get_coordinator_status()
        assert status2["active_leases"] == 0

    def test_coordinator_health(self):
        coord = DistributedExperimentCoordinator()
        status = coord.get_coordinator_status()
        assert status["coordinator_healthy"] is True


class TestResilienceAuditTrailService:
    def test_record_and_retrieve_audit(self):
        svc = ResilienceAuditTrailService()
        record_id = svc.record_audit_event("EXPERIMENT_STARTED", "exp_001", {"note": "Chaos injection"})
        assert record_id.startswith("audit_")
        trail = svc.get_audit_trail("exp_001")
        assert len(trail) == 1
        assert trail[0]["event_type"] == "EXPERIMENT_STARTED"

    def test_multiple_audit_events(self):
        svc = ResilienceAuditTrailService()
        for i in range(5):
            svc.record_audit_event(f"EVENT_{i}", "exp_multi")
        trail = svc.get_audit_trail("exp_multi")
        assert len(trail) == 5


class TestResilienceHealthService:
    def test_get_platform_health(self):
        svc = ResilienceHealthService()
        health = svc.get_platform_health()
        assert health["platform5_status"] == "HEALTHY"


class TestResilienceObservabilityService:
    def test_get_observability_metrics(self):
        svc = ResilienceObservabilityService()
        metrics = svc.get_observability_metrics()
        assert metrics["sla_compliance_pct"] == 100.0
        assert metrics["average_confidence_score"] >= 95.0
