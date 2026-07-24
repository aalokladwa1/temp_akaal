"""Tests for 6 Domain Replicators covering all 25 Capabilities."""

import pytest
from akaal.replication.core.context import ReplicationContext
from akaal.replication.domain.core_replication import CoreReplicationDomain
from akaal.replication.domain.conflict_management import ConflictManagementDomain
from akaal.replication.domain.observability_domain import ObservabilityDomain
from akaal.replication.domain.recovery_domain import RecoveryDomain
from akaal.replication.domain.intelligence_domain import IntelligenceDomain
from akaal.replication.domain.governance_domain import GovernanceDomain


@pytest.mark.asyncio
async def test_core_replication_domain():
    domain = CoreReplicationDomain()
    assert len(domain.capabilities) == 4
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"
    assert res.total_actions == 2


@pytest.mark.asyncio
async def test_conflict_management_domain():
    domain = ConflictManagementDomain()
    assert len(domain.capabilities) == 4
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_observability_domain():
    domain = ObservabilityDomain()
    assert len(domain.capabilities) == 2
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_recovery_domain():
    domain = RecoveryDomain()
    assert len(domain.capabilities) == 6
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_intelligence_domain():
    domain = IntelligenceDomain()
    assert len(domain.capabilities) == 6
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"


@pytest.mark.asyncio
async def test_governance_domain():
    domain = GovernanceDomain()
    assert len(domain.capabilities) == 3
    ctx = ReplicationContext()
    res = await domain.replicate_domain(ctx)
    assert res.status.value == "COMPLETED"
