"""
tests.unit.engine_fabric.test_p7b26_multi_region_operation
===============================================================
P7B.26 -- Multi-Region Operation hostile test suite.

Includes the MANDATORY sovereignty-under-failure scenario required by the P7B Group-3
directive: an India-only workload's Mumbai execution site becomes unavailable; Singapore
is healthy, capable, and reachable -- but Singapore MUST be rejected by residency, and
with zero compliant placement remaining, the correct outcome is no placement, never a
silent weakening of the policy to preserve availability.

Every test below composes ONLY: P7B.24 SiteCoordinator (unmodified), P7B.26's own
region-health/candidate-curation functions, and the UNMODIFIED Group-2
akaalEngine.fabric.placement.engine.evaluate_candidates + residency/capability evaluators
-- proving P7B.26 introduces no second placement/residency authority.
"""

from __future__ import annotations

import time

import pytest

from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.engine import evaluate_candidates
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.regional_operation import (
    RegionOperationalState,
    UNKNOWN_REGION_LABEL,
    compute_region_health,
    curate_regional_candidates,
    get_region_state,
    region_of,
)
from akaalEngine.fabric.site_coordination import CoordinationView, SiteCoordinator, SiteHeartbeat
from akaalEngine.fabric.execution_site.models import SiteHealthState


def _trusted_site(registry: SiteRegistry, site_id, tenant_id="tenant-a", region=None, environment_id="env-1", capabilities=frozenset()):
    site = ExecutionSite(
        site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id=environment_id,
        region=region, claimed_security_identity=f"spiffe://akaal.local/site/{site_id}",
        capabilities=capabilities,
    )
    registry.register(site)
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry.get(site_id)


def _india_only_policy():
    return ResidencyPolicy(
        policy_id="india-only",
        dimension=LocalityDimension.COUNTRY,
        allowed_values=frozenset({"IN"}),
        required_roles=(LocalitySubjectRole.EXECUTION_SITE,),
    )


def _proven_country_locality(site_id, tenant_id, country):
    return LocalityRecord(
        subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=tenant_id,
        country=country, confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )


# ----------------------------------------------------------------------
# Region health rollup
# ----------------------------------------------------------------------

def test_region_healthy_with_one_available_site():
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region="ap-south-1")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    health = compute_region_health([site], coord)
    assert health["ap-south-1"].state == RegionOperationalState.HEALTHY


def test_region_degraded_when_only_degraded_sites():
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region="ap-south-1")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.DEGRADED))
    health = compute_region_health([site], coord)
    assert health["ap-south-1"].state == RegionOperationalState.DEGRADED


def test_region_unavailable_when_all_sites_stale():
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region="ap-south-1")
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    health = compute_region_health([site], coord)
    assert health["ap-south-1"].state == RegionOperationalState.UNAVAILABLE
    assert "site-1" in health["ap-south-1"].unavailable_site_ids


def test_region_absent_entirely_reports_unknown_not_healthy():
    registry = SiteRegistry()
    coord = SiteCoordinator(registry)
    health = compute_region_health([], coord)
    assert get_region_state(health, "ap-south-1") == RegionOperationalState.UNKNOWN


def test_site_with_no_declared_region_uses_unknown_region_label():
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region=None)
    assert region_of(site) == UNKNOWN_REGION_LABEL


# ----------------------------------------------------------------------
# Candidate curation -- pure curation, no placement decision
# ----------------------------------------------------------------------

def test_curate_excludes_individually_stale_site_even_in_otherwise_named_region():
    registry = SiteRegistry()
    stale_site = _trusted_site(registry, "site-stale", region="r1")
    fresh_site = _trusted_site(registry, "site-fresh", region="r1")
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-stale", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-fresh", sequence=1, reported_health=SiteHealthState.HEALTHY))

    candidates, health = curate_regional_candidates([stale_site, fresh_site], coord)
    assert [c.site_id for c in candidates] == ["site-fresh"]
    assert health["r1"].state == RegionOperationalState.HEALTHY  # region has ONE healthy site


def test_curate_excludes_manually_specified_failed_region():
    registry = SiteRegistry()
    mumbai = _trusted_site(registry, "site-mumbai", region="ap-south-1")
    singapore = _trusted_site(registry, "site-singapore", region="ap-southeast-1")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-mumbai", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=1, reported_health=SiteHealthState.HEALTHY))

    candidates, _ = curate_regional_candidates([mumbai, singapore], coord, exclude_regions=("ap-south-1",))
    assert [c.site_id for c in candidates] == ["site-singapore"]


def test_curate_never_returns_a_revoked_site_regardless_of_heartbeat_history():
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region="r1")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    registry.revoke("site-1", reason="hostile-test revocation")
    candidates, health = curate_regional_candidates([site], coord)
    assert candidates == []
    assert health["r1"].state == RegionOperationalState.UNAVAILABLE


def test_curation_returns_execution_site_objects_only_no_verdict():
    """curate_regional_candidates must never itself claim a candidate is placement-usable
    -- it returns raw ExecutionSite objects for evaluate_candidates to judge."""
    registry = SiteRegistry()
    site = _trusted_site(registry, "site-1", region="r1")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    candidates, _ = curate_regional_candidates([site], coord)
    assert all(isinstance(c, ExecutionSite) for c in candidates)
    assert not hasattr(candidates[0], "is_compliant")


# ----------------------------------------------------------------------
# THE MANDATORY SOVEREIGNTY-UNDER-FAILURE SCENARIO
# ----------------------------------------------------------------------

def test_mandatory_india_only_mumbai_down_singapore_rejected():
    """
    India-only migration -> Mumbai execution site becomes unavailable -> Singapore is
    healthy, capable, and reachable -- but Singapore MUST be rejected on RESIDENCY, and
    with zero compliant candidates remaining, evaluate_candidates must report NO
    COMPLIANT PLACEMENT (never silently accept Singapore to preserve availability).
    """
    registry = SiteRegistry()
    cap = frozenset({"postgresql"})
    mumbai = _trusted_site(registry, "site-mumbai", region="ap-south-1", capabilities=cap)
    singapore = _trusted_site(registry, "site-singapore", region="ap-southeast-1", capabilities=cap)

    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-mumbai", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=1, reported_health=SiteHealthState.HEALTHY))

    # Mumbai fails -- stops heartbeating; Singapore keeps heartbeating (healthy, cheaper).
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, health = curate_regional_candidates([mumbai, singapore], coord)
    assert health["ap-south-1"].state == RegionOperationalState.UNAVAILABLE
    assert health["ap-southeast-1"].state == RegionOperationalState.HEALTHY
    assert [c.site_id for c in candidates] == ["site-singapore"]  # Mumbai correctly excluded by liveness alone

    requirement = CapabilityRequirement(required_capabilities=cap, plan_reference="plan-india-only-1")
    result = evaluate_candidates(
        plan_reference="plan-india-only-1",
        candidates=candidates,
        capability_requirement=requirement,
        actor_context={"actor": "test"},
        authorization_action="execute",
        authorization_callback=lambda site, actor, action, context: True,
        residency_policies=(_india_only_policy(),),
        locality_by_site={"site-singapore": {LocalitySubjectRole.EXECUTION_SITE: _proven_country_locality("site-singapore", "tenant-a", "SG")}},
        tenant_id="tenant-a",
    )

    assert not result.has_compliant_placement()
    assert result.accepted == ()
    assert result.rejected[0].site_id == "site-singapore"
    assert result.rejected[0].stage == "RESIDENCY"


def test_failover_succeeds_when_a_compliant_alternate_india_site_exists():
    """Contrast case: Mumbai fails, but Delhi (also India, proven) is healthy -- failover
    to a residency-compliant alternate MUST succeed; residency is not an all-or-nothing
    'refuse every failover' rule, only 'never accept a non-compliant one'."""
    registry = SiteRegistry()
    cap = frozenset({"postgresql"})
    mumbai = _trusted_site(registry, "site-mumbai", region="ap-south-1", capabilities=cap)
    delhi = _trusted_site(registry, "site-delhi", region="ap-south-2", capabilities=cap)

    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-mumbai", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-delhi", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-delhi", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, _ = curate_regional_candidates([mumbai, delhi], coord)
    assert [c.site_id for c in candidates] == ["site-delhi"]

    requirement = CapabilityRequirement(required_capabilities=cap, plan_reference="plan-india-only-2")
    result = evaluate_candidates(
        plan_reference="plan-india-only-2",
        candidates=candidates,
        capability_requirement=requirement,
        actor_context={"actor": "test"},
        authorization_action="execute",
        authorization_callback=lambda site, actor, action, context: True,
        residency_policies=(_india_only_policy(),),
        locality_by_site={"site-delhi": {LocalitySubjectRole.EXECUTION_SITE: _proven_country_locality("site-delhi", "tenant-a", "IN")}},
        tenant_id="tenant-a",
    )
    assert result.has_compliant_placement()
    assert result.accepted[0].site_id == "site-delhi"


def test_zero_physical_effect_when_no_compliant_region_remains():
    """When evaluate_candidates reports no compliant placement, a caller must never
    attempt any physical effect. This test proves the SIGNAL, not the caller's downstream
    discipline (that is proven at the Pipeline/Ownership integration boundary)."""
    registry = SiteRegistry()
    cap = frozenset({"postgresql"})
    singapore = _trusted_site(registry, "site-singapore", region="ap-southeast-1", capabilities=cap)
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=1, reported_health=SiteHealthState.HEALTHY))
    candidates, _ = curate_regional_candidates([singapore], coord)

    requirement = CapabilityRequirement(required_capabilities=cap, plan_reference="plan-india-only-3")
    result = evaluate_candidates(
        plan_reference="plan-india-only-3", candidates=candidates, capability_requirement=requirement,
        actor_context={}, authorization_action="execute", authorization_callback=lambda *a: True,
        residency_policies=(_india_only_policy(),),
        locality_by_site={"site-singapore": {LocalitySubjectRole.EXECUTION_SITE: _proven_country_locality("site-singapore", "tenant-a", "SG")}},
        tenant_id="tenant-a",
    )
    should_attempt_physical_effect = result.has_compliant_placement()
    assert should_attempt_physical_effect is False
