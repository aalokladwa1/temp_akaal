"""Tests for healing infrastructure services (RootCause, Verification, Scoring, Rollback, PatternLearning, Recommendation, Audit, Observability)."""

import pytest
from akaal.healing.services.root_cause import RootCauseAnalysisService
from akaal.healing.services.verification import RepairVerificationService
from akaal.healing.services.scoring import ConfidenceScoringService
from akaal.healing.services.rollback import RollbackService
from akaal.healing.services.pattern_learning import PatternLearningService
from akaal.healing.services.recommendation import RecommendationEngineService
from akaal.healing.services.audit import RepairAuditTrailService
from akaal.healing.services.observability import ObservabilityService
from akaal.healing.events.event_bus import HealingEventBus
from akaal.healing.events.events import HealingEvent, HealingEventType
from akaal.healing.events.subscribers import HealingMetricsSubscriber
from akaal.healing.distributed.coordinator import DistributedHealingCoordinator


def test_root_cause_service():
    svc = RootCauseAnalysisService()
    diag = svc.analyze_failure(None)
    assert diag["root_cause"] == "SCHEMA_OR_DATA_DRIFT"


def test_confidence_scoring_service():
    svc = ConfidenceScoringService()
    score = svc.compute_confidence(None)
    assert score.overall_confidence > 90.0


def test_pattern_learning_and_recommendations():
    learn = PatternLearningService()
    learn.record_pattern("MISSING_ROW", "AUTO_RESTORE", 10.0)
    pat = learn.get_pattern("MISSING_ROW")
    assert pat["success_count"] == 1

    rec = RecommendationEngineService()
    rec_res = rec.recommend_repair_strategy(None)
    assert rec_res["confidence"] > 0.90


def test_observability_service():
    obs = ObservabilityService()
    obs.record_repair_result(True, 1.5)
    snap = obs.get_telemetry()
    assert snap["total_repairs"] == 1
    assert snap["successful_repairs"] == 1


@pytest.mark.asyncio
async def test_healing_event_bus():
    bus = HealingEventBus()
    sub = HealingMetricsSubscriber()
    bus.subscribe_all(sub.on_event)

    await bus.publish(HealingEvent(event_type=HealingEventType.REPAIR_STARTED, payload={}))
    assert sub.event_counts.get("RepairStarted") == 1


@pytest.mark.asyncio
async def test_distributed_healing_coordinator():
    coord = DistributedHealingCoordinator(num_workers=2)
    tasks = coord.scheduler.partition_repair_tasks("CoreRepairDomain", "Cap 1", ["users", "orders"])
    results = await coord.run_distributed_healing(tasks, None)
    assert len(results) == 2
