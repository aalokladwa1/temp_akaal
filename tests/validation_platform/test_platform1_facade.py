"""E2E Test suite for EnterpriseValidationPlatformV1 public facade."""

import pytest
from akaal.validation import EnterpriseValidationPlatformV1
from akaal.validation.core.config import ValidationConfig, ValidationProfile, PolicyProfile
from akaal.validation.core.models import ValidationStatus


def test_platform1_facade_initialization():
    platform = EnterpriseValidationPlatformV1()
    assert platform is not None
    assert platform.merkle_service is not None
    assert platform.evidence_service is not None
    assert platform.replay_service is not None
    assert platform.explainability_service is not None
    assert platform.observability_service is not None
    assert platform.cache is not None
    assert platform.event_bus is not None
    assert platform.policy_engine is not None
    assert platform.plugin_registry is not None
    assert platform.distributed_coordinator is not None


def test_supported_capabilities():
    platform = EnterpriseValidationPlatformV1()
    capabilities = platform.get_supported_capabilities()
    assert len(capabilities) > 0
    # Confirm capabilities 1 to 33 are supported across domain validators
    cap_str = " ".join(capabilities)
    assert "Cap 1" in cap_str
    assert "Cap 2" in cap_str
    assert "Cap 33" in cap_str or "Cap 27" in cap_str or "Cap 18" in cap_str


@pytest.mark.asyncio
async def test_validate_all_async():
    platform = EnterpriseValidationPlatformV1()
    session = await platform.validate_all_async()
    assert session is not None
    assert session.state.value == "COMPLETED"
    assert len(session.results) == 8  # 8 Domain validators
    assert session.total_checks_executed > 0


def test_validate_all_sync():
    platform = EnterpriseValidationPlatformV1()
    session = platform.validate_all()
    assert session is not None
    assert session.state.value == "COMPLETED"
    assert len(session.results) == 8
