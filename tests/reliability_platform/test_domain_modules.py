"""Tests for 6 Domain Reliability Modules."""

import pytest
from akaal.reliability.domain.reliability_domain import ReliabilityDomain
from akaal.reliability.domain.recovery_domain import RecoveryDomain
from akaal.reliability.domain.diagnostics_domain import DiagnosticsDomain
from akaal.reliability.domain.resilience_domain import ResilienceDomain
from akaal.reliability.domain.governance_domain import GovernanceDomain
from akaal.reliability.domain.observability_domain import ObservabilityDomain
from akaal.reliability.core.context import ReliabilityContext


@pytest.mark.asyncio
async def test_reliability_domain():
    domain = ReliabilityDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "ReliabilityDomain"
    assert res.total_actions == 4


@pytest.mark.asyncio
async def test_recovery_domain():
    domain = RecoveryDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "RecoveryDomain"
    assert res.total_actions == 5


@pytest.mark.asyncio
async def test_diagnostics_domain():
    domain = DiagnosticsDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "DiagnosticsDomain"
    assert res.total_actions == 5


@pytest.mark.asyncio
async def test_resilience_domain():
    domain = ResilienceDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "ResilienceDomain"
    assert res.total_actions == 6


@pytest.mark.asyncio
async def test_governance_domain():
    domain = GovernanceDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "GovernanceDomain"
    assert res.total_actions == 2


@pytest.mark.asyncio
async def test_observability_domain():
    domain = ObservabilityDomain()
    ctx = ReliabilityContext()
    res = await domain.execute_domain(ctx)
    assert res.domain_name == "ObservabilityDomain"
    assert res.total_actions == 2
