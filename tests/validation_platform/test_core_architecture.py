"""Tests for core abstractions: ValidationContext, models, registry, pipeline."""

import pytest
from akaal.validation.core.context import ValidationContext
from akaal.validation.core.config import ValidationConfig
from akaal.validation.core.models import ValidationResult, ValidationStatus, ValidationIssue, SeverityLevel
from akaal.validation.core.registry import ValidatorRegistry
from akaal.validation.pipeline.orchestrator import ValidationPipeline
from akaal.validation.domain.structural import StructuralValidator


def test_validation_context_immutability():
    ctx1 = ValidationContext()
    ctx2 = ctx1.with_overrides(temp_storage="/custom/path")
    assert ctx1.temp_storage == "/tmp/akaal_validation"
    assert ctx2.temp_storage == "/custom/path"


def test_validator_registry():
    reg = ValidatorRegistry()
    struct_val = StructuralValidator()
    reg.register_domain_validator(struct_val)

    assert reg.get_domain_validator("StructuralDomain") == struct_val
    assert reg.get_validator_for_capability("Cap 1") == struct_val
    assert "StructuralDomain" in reg.list_domains()


def test_validation_result_merge():
    res1 = ValidationResult(
        domain_name="D1",
        capabilities_tested=["Cap 1"],
        status=ValidationStatus.PASSED,
        passed_count=10,
    )
    res2 = ValidationResult(
        domain_name="D2",
        capabilities_tested=["Cap 2"],
        status=ValidationStatus.PASSED,
        passed_count=20,
    )
    merged = res1.merge(res2)
    assert merged.passed_count == 30
    assert len(merged.capabilities_tested) == 2
