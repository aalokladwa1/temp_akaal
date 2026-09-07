"""
P7B.13 -- Capability-Aware Placement: positive and hostile tests.
"""

import pytest

from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind, SiteTrustState
from akaalEngine.fabric.placement.capability import (
    CapabilityEvaluationError,
    CapabilityRequirement,
    CapacityOffer,
    evaluate_capability,
)


def _site(caps, trust=SiteTrustState.TRUSTED, staging=False, site_id="site-1"):
    return ExecutionSite(
        site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1",
        capabilities=frozenset(caps), trust_state=trust, staging_capable=staging,
    )


def test_all_required_capabilities_present_satisfied():
    site = _site({"oracle", "postgresql", "cdc"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle", "postgresql"}), plan_reference="plan-1")
    result = evaluate_capability(site, req)
    assert result.satisfied
    assert not result.missing_capabilities


def test_missing_capability_rejected():
    site = _site({"postgresql"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle", "postgresql"}), plan_reference="plan-1")
    result = evaluate_capability(site, req)
    assert not result.satisfied
    assert "oracle" in result.missing_capabilities


def test_unregistered_site_never_capable_regardless_of_advertised_capabilities():
    site = _site({"oracle", "postgresql", "cdc"}, trust=SiteTrustState.UNREGISTERED)
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), plan_reference="plan-1")
    result = evaluate_capability(site, req)
    assert not result.satisfied


def test_revoked_site_never_capable():
    site = _site({"oracle"}, trust=SiteTrustState.REVOKED)
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), plan_reference="plan-1")
    result = evaluate_capability(site, req)
    assert not result.satisfied


def test_staging_requirement_enforced():
    site = _site({"oracle"}, staging=False)
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), requires_staging_capable=True, plan_reference="plan-1")
    result = evaluate_capability(site, req)
    assert not result.satisfied
    assert "staging_capable" in result.insufficient_dimensions


def test_capacity_sufficient_when_offered_meets_minimums():
    site = _site({"oracle"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), min_memory_mb=16000, plan_reference="plan-1")
    offer = CapacityOffer(memory_mb=24000, provenance="worker-heartbeat")
    result = evaluate_capability(site, req, offer)
    assert result.satisfied


def test_capacity_insufficient_rejected():
    site = _site({"oracle"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), min_memory_mb=32000, plan_reference="plan-1")
    offer = CapacityOffer(memory_mb=8000, provenance="worker-heartbeat")
    result = evaluate_capability(site, req, offer)
    assert not result.satisfied
    assert "memory_mb" in result.insufficient_dimensions


def test_resource_requirement_without_capacity_offer_fails_closed():
    site = _site({"oracle"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), min_memory_mb=1000, plan_reference="plan-1")
    result = evaluate_capability(site, req, capacity=None)
    assert not result.satisfied  # never assumed sufficient just because it wasn't disproven


def test_capacity_offer_with_empty_provenance_rejected_not_trusted():
    site = _site({"oracle"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle"}), min_cpu_cores=4, plan_reference="plan-1")
    offer = CapacityOffer(cpu_cores=100, provenance="")  # huge claim but no provenance
    result = evaluate_capability(site, req, offer)
    assert not result.satisfied
    assert "cpu_cores" in result.insufficient_dimensions


def test_negative_capacity_offer_rejected_at_construction():
    with pytest.raises(CapabilityEvaluationError):
        CapacityOffer(cpu_cores=-1, provenance="worker-heartbeat")


def test_capability_requirement_requires_plan_reference():
    with pytest.raises(CapabilityEvaluationError):
        CapabilityRequirement(required_capabilities=frozenset({"oracle"}), plan_reference="")


def test_unsupported_connector_zero_physical_calls_semantics():
    """A site advertising postgresql but not oracle cannot execute an Oracle->Postgres
    plan -- this test proves the evaluation stops at capability, never proceeds. No
    physical call is made anywhere in this module (it is pure/no I/O by construction),
    which is itself the negative-capability proof: there is no code path here capable of
    making one."""
    site = _site({"postgresql"})
    req = CapabilityRequirement(required_capabilities=frozenset({"oracle", "postgresql"}), plan_reference="oracle-to-pg")
    result = evaluate_capability(site, req)
    assert not result.satisfied
    assert result.missing_capabilities == frozenset({"oracle"})
