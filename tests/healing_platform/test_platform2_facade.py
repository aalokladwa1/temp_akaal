"""E2E Test suite for EnterpriseSelfHealingPlatformV2 canonical facade."""

import pytest
from akaal.healing import EnterpriseSelfHealingPlatformV2
from akaal.healing.core.config import HealingConfig, HealingProfile, ApprovalMode


def test_platform2_facade_initialization():
    platform = EnterpriseSelfHealingPlatformV2()
    assert platform is not None
    assert platform.validation_platform is not None
    assert platform.decision_engine is not None
    assert platform.dependency_graph is not None
    assert platform.sandbox_engine is not None
    assert platform.repair_scheduler is not None
    assert platform.multi_source_recovery is not None
    assert platform.lock_manager is not None
    assert platform.business_analyzer is not None
    assert platform.root_cause_service is not None
    assert platform.verification_service is not None
    assert platform.scoring_service is not None
    assert platform.rollback_service is not None
    assert platform.pattern_learning_service is not None
    assert platform.recommendation_service is not None
    assert platform.audit_service is not None
    assert platform.observability_service is not None
    assert platform.cache is not None
    assert platform.event_bus is not None
    assert platform.policy_engine is not None
    assert platform.distributed_coordinator is not None


def test_supported_capabilities():
    platform = EnterpriseSelfHealingPlatformV2()
    caps = platform.get_supported_capabilities()
    assert len(caps) > 0
    cap_str = " ".join(caps)
    assert "Cap 1" in cap_str
    assert "Cap 25" in cap_str


@pytest.mark.asyncio
async def test_heal_all_async():
    platform = EnterpriseSelfHealingPlatformV2()
    session = await platform.heal_all_async()
    assert session is not None
    assert session.state.value == "COMPLETED"
    assert len(session.results) == 6  # 6 Domain healers
    assert session.total_repairs_executed > 0


def test_heal_all_sync():
    platform = EnterpriseSelfHealingPlatformV2()
    session = platform.heal_all()
    assert session is not None
    assert session.state.value == "COMPLETED"
    assert len(session.results) == 6
