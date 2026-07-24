"""Tests for all 6 Domain Healers covering 25 self-healing capabilities."""

import pytest
from akaal.healing.core.context import HealingContext
from akaal.healing.domain.core_repair import CoreRepairHealer
from akaal.healing.domain.intelligent import IntelligentHealer
from akaal.healing.domain.safe_execution import SafeExecutionHealer
from akaal.healing.domain.recovery import EnterpriseRecoveryHealer
from akaal.healing.domain.governance import GovernanceHealer
from akaal.healing.domain.learning import LearningHealer


@pytest.mark.asyncio
async def test_all_domain_healers():
    ctx = HealingContext()

    healers = [
        CoreRepairHealer(),
        IntelligentHealer(),
        SafeExecutionHealer(),
        EnterpriseRecoveryHealer(),
        GovernanceHealer(),
        LearningHealer(),
    ]

    total_caps = []
    for healer in healers:
        res = await healer.heal_domain(ctx)
        assert res is not None
        assert res.domain_name == healer.domain_name
        assert len(res.capabilities_executed) > 0
        total_caps.extend(res.capabilities_executed)

    assert len(healers) == 6
    assert len(total_caps) == 25
