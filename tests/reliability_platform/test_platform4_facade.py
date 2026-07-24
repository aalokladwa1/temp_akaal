"""Tests for EnterpriseReliabilityPlatformV4 Public Facade."""

import pytest
from akaal.reliability.facade.platform4 import EnterpriseReliabilityPlatformV4
from akaal.reliability.core.session import ReliabilitySession
from akaal.integration.composition_root import EnterpriseLifecycleManager, CrossPlatformContext


def test_platform4_facade_initialization():
    platform = EnterpriseReliabilityPlatformV4()
    assert platform.decision_engine is not None
    assert platform.state_machine is not None
    assert platform.knowledge_base is not None
    assert platform.incident_timeline is not None


def test_platform4_sync_execution():
    platform = EnterpriseReliabilityPlatformV4()
    session = platform.run_reliability_suite()
    assert isinstance(session, ReliabilitySession)
    assert session.is_successful is True
    assert len(session.results) == 6


@pytest.mark.asyncio
async def test_platform4_async_execution():
    platform = EnterpriseReliabilityPlatformV4()
    session = await platform.run_reliability_suite_async()
    assert isinstance(session, ReliabilitySession)
    assert session.is_successful is True
    assert session.total_actions_executed == 24


def test_composition_root_integration():
    mgr = EnterpriseLifecycleManager()
    context = mgr.bootstrap()
    assert isinstance(context, CrossPlatformContext)
    assert hasattr(context, "reliability_platform")
    assert context.reliability_platform is not None
