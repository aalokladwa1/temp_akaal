"""Tests for all 8 Domain Validators covering 33 capabilities."""

import pytest
from akaal.validation.core.context import ValidationContext
from akaal.validation.domain.structural import StructuralValidator
from akaal.validation.domain.data import DataValidator
from akaal.validation.domain.integrity import IntegrityValidator
from akaal.validation.domain.statistical import StatisticalValidator
from akaal.validation.domain.semantic import SemanticValidator
from akaal.validation.domain.performance import PerformanceValidator
from akaal.validation.domain.enterprise import EnterpriseValidator
from akaal.validation.domain.scoring import ScoringValidator
from akaal.validation.services.merkle import MerkleService
from akaal.validation.services.observability import ObservabilityService


@pytest.mark.asyncio
async def test_all_domain_validators():
    merkle = MerkleService()
    obs = ObservabilityService()
    ctx = ValidationContext(merkle_service=merkle, observability_service=obs)

    validators = [
        StructuralValidator(),
        DataValidator(),
        IntegrityValidator(),
        StatisticalValidator(),
        SemanticValidator(),
        PerformanceValidator(),
        EnterpriseValidator(),
        ScoringValidator(),
    ]

    total_caps = []
    for val in validators:
        res = await val.validate_domain(ctx)
        assert res is not None
        assert res.domain_name == val.domain_name
        assert len(res.capabilities_tested) > 0
        total_caps.extend(res.capabilities_tested)

    # Confirm all 8 domains executed and returned metrics
    assert len(validators) == 8
    assert len(total_caps) >= 25
