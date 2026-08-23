"""
tests.unit.engine_extensions.test_capability_truth
==================================================
Tests for capability truth resolution, fail-closed handling on unknown capabilities, and dependency-conditioned evaluation.
"""

from akaalEngine.extensions.dependencies.diagnostics import DependencyDiagnosticReport
from akaalEngine.extensions.models.capability import CapabilityDeclaration
from akaalEngine.extensions.models.dependency import (
    DependencyDiagnostic,
    DependencyStatus,
    DependencyType,
)
from akaalEngine.extensions.models.enums import ExtensionLifecycleState, ProofLevel
from akaalEngine.extensions.truth.capability_resolver import CapabilityTruthResolver


def test_capability_truth_fail_closed_on_unknown():
    truth = CapabilityTruthResolver.resolve_capability_truth(
        declaration=None,
        capability_name="LOGICAL_REPLICATION",
        lifecycle_state=ExtensionLifecycleState.ACTIVE,
    )
    assert not truth.is_supported
    assert "not declared or explicitly unsupported" in (truth.diagnostic or "")


def test_capability_truth_dependency_conditioned():
    decl = CapabilityDeclaration(capability_name="COMPRESSION", is_supported=True)

    # Missing mandatory dependency
    missing_diag = DependencyDiagnostic(
        dependency_name="zstandard",
        dep_type=DependencyType.PYTHON_PACKAGE,
        status=DependencyStatus.MISSING,
        is_optional=False,
    )
    report = DependencyDiagnosticReport(target_id="p1", diagnostics=(missing_diag,))

    truth = CapabilityTruthResolver.resolve_capability_truth(
        declaration=decl,
        capability_name="COMPRESSION",
        lifecycle_state=ExtensionLifecycleState.ACTIVE,
        dep_report=report,
    )
    assert not truth.is_supported
    assert not truth.is_dependency_satisfied
    assert "zstandard" in truth.missing_dependencies


def test_capability_truth_lifecycle_disabled():
    decl = CapabilityDeclaration(capability_name="BULK_READ", is_supported=True)

    truth = CapabilityTruthResolver.resolve_capability_truth(
        declaration=decl,
        capability_name="BULK_READ",
        lifecycle_state=ExtensionLifecycleState.UNAVAILABLE,
    )
    assert not truth.is_supported
    assert "disables capability support" in (truth.diagnostic or "")
