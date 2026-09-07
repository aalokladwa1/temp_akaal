"""
tests.unit.engine_fabric.test_p7b28_disaster_recovery_failover
===================================================================
P7B.28 -- Disaster Recovery & Geo Failover hostile test suite.

Proves attempt_failover (composed over P7B.24 SiteCoordinator, P7B.25 OwnershipManager,
and the UNMODIFIED Group-2 evaluate_candidates -- no second migration/placement/ownership
authority) enforces the full Group-3 failure/recovery pathway, including the MANDATORY
India-only-sovereignty-survives-failover scenario with real ownership fencing (extending
P7B.26's placement-only proof with the ownership-transfer half of the story).
"""

from __future__ import annotations

import time

import pytest

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.durability.models.state import DurabilityConfig
from akaalEngine.durability.store.sqlite import SQLiteWalBackend
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.execution_site.models import SiteHealthState
from akaalEngine.fabric.failover import FailoverOutcome, attempt_failover
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.ownership import OwnershipClaim, OwnershipManager
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.regional_operation import curate_regional_candidates
from akaalEngine.fabric.site_coordination import SiteCoordinator, SiteHeartbeat

FENCING_KEY = b"p7b28-fencing-signing-key-000001"
ANCHOR_KEY = b"p7b28-journal-anchor-key-0000002"


def _fencing_manager(tmp_path, name="fencing.db"):
    cfg = DurabilityConfig(storage_dir=str(tmp_path / name), fencing_signing_key=FENCING_KEY, journal_anchor_key=ANCHOR_KEY)
    backend = SQLiteWalBackend(cfg)
    backend.initialize()
    return FencingTokenManager(backend, signing_key=FENCING_KEY)


def _trusted_site(registry, site_id, tenant_id="tenant-a", region=None, capabilities=frozenset()):
    registry.register(ExecutionSite(
        site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id="env-1", region=region,
        claimed_security_identity=f"spiffe://akaal.local/site/{site_id}", capabilities=capabilities,
    ))
    registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry.get(site_id)


def _claim_for(site, *, tenant_id="tenant-a", migration_id="mig-1", plan_id="plan-1", worker_id=None):
    return OwnershipClaim(
        tenant_id=tenant_id, workspace_id="ws-1", project_id="proj-1", migration_id=migration_id,
        plan_id=plan_id, plan_fingerprint="fp-1", execution_identity_seal_fingerprint="seal-1",
        execution_id="exec-1", placement_id="place-1", assignment_id="assign-1",
        site_id=site.site_id, worker_id=worker_id or f"worker-{site.site_id}", correlation_id="corr-1",
        ttl_seconds=30.0,
    )


def _india_only_policy():
    return ResidencyPolicy(
        policy_id="india-only", dimension=LocalityDimension.COUNTRY,
        allowed_values=frozenset({"IN"}), required_roles=(LocalitySubjectRole.EXECUTION_SITE,),
    )


def _proven_country(site_id, tenant_id, country):
    return LocalityRecord(
        subject_ref=site_id, subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id=tenant_id,
        country=country, confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )


# ----------------------------------------------------------------------
# Refuse failover when there's nothing to fail over
# ----------------------------------------------------------------------

def test_failover_refused_when_old_site_is_still_healthy(tmp_path):
    registry = SiteRegistry()
    site_a = _trusted_site(registry, "site-a", region="r1")
    site_b = _trusted_site(registry, "site-b", region="r2")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(site_a))

    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=[site_b], plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    assert result.outcome == FailoverOutcome.NOT_REQUIRED
    # Old ownership must remain untouched/valid.
    revalidated = om.validate(old.ownership_key, old.lease_id, old.fencing_generation)
    assert revalidated.fencing_generation == old.fencing_generation


def test_failover_no_op_when_no_ownership_ever_existed(tmp_path):
    registry = SiteRegistry()
    site_b = _trusted_site(registry, "site-b", region="r2")
    coord = SiteCoordinator(registry)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=1, reported_health=SiteHealthState.HEALTHY))
    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))

    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key="tenant-a::mig-1::plan-1",
        candidates=[site_b], plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    assert result.outcome == FailoverOutcome.SUCCEEDED
    assert result.new_record.fencing_generation == 1


# ----------------------------------------------------------------------
# Genuine failure -> fence old owner -> reassign
# ----------------------------------------------------------------------

def test_failover_fences_old_owner_and_reassigns_to_healthy_site(tmp_path):
    registry = SiteRegistry()
    site_a = _trusted_site(registry, "site-a", region="r1")
    site_b = _trusted_site(registry, "site-b", region="r2")
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(site_a))

    time.sleep(0.12)  # site-a goes stale; site-b keeps heartbeating
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=2, reported_health=SiteHealthState.HEALTHY))

    # In real usage `candidates` is pre-curated by liveness (P7B.26); attempt_failover
    # itself makes no liveness decision, only capability/authorization/residency (via
    # evaluate_candidates) and ownership fencing/reassignment.
    candidates, _ = curate_regional_candidates([site_a, site_b], coord)
    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=candidates, plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    assert result.outcome == FailoverOutcome.SUCCEEDED
    assert result.selected_site_id == "site-b"
    assert result.new_record.fencing_generation == old.fencing_generation + 1

    # Old owner is now fenced -- cannot continue physical effects.
    with pytest.raises(Exception):
        om.validate(old.ownership_key, old.lease_id, old.fencing_generation)


def test_old_site_return_after_failover_does_not_regain_authority(tmp_path):
    """Old site A comes back online (starts heartbeating again) AFTER B has taken over --
    A's stale generation must never again validate as current owner."""
    registry = SiteRegistry()
    site_a = _trusted_site(registry, "site-a", region="r1")
    site_b = _trusted_site(registry, "site-b", region="r2")
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(site_a))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, _ = curate_regional_candidates([site_a, site_b], coord)
    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=candidates, plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    assert result.selected_site_id == "site-b"

    # Site A "returns" -- resumes heartbeating with its stale fencing_epoch_seen.
    site_a_epoch = registry.current_fencing_epoch("site-a")
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=2, reported_health=SiteHealthState.HEALTHY, fencing_epoch_seen=site_a_epoch))
    # Heartbeat acceptance (a P7B.24 liveness concern) does not resurrect P7B.25 ownership.
    with pytest.raises(Exception):
        om.validate(old.ownership_key, old.lease_id, old.fencing_generation)


def test_duplicate_failover_request_is_idempotent_not_double_fenced(tmp_path):
    registry = SiteRegistry()
    site_a = _trusted_site(registry, "site-a", region="r1")
    site_b = _trusted_site(registry, "site-b", region="r2")
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(site_a))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-b", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, _ = curate_regional_candidates([site_a, site_b], coord)
    kwargs = dict(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=candidates, plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    result1 = attempt_failover(**kwargs)
    result2 = attempt_failover(**kwargs)  # e.g. two concurrent controllers both detect the failure

    assert result1.outcome == FailoverOutcome.SUCCEEDED
    # Second call: new owner (site-b) is healthy and holds a valid, unexpired lease --
    # correctly refused as NOT_REQUIRED rather than reassigning yet again.
    assert result2.outcome == FailoverOutcome.NOT_REQUIRED
    assert result2.old_record.fencing_generation == result1.new_record.fencing_generation


# ----------------------------------------------------------------------
# No compliant candidate -> fail safe
# ----------------------------------------------------------------------

def test_no_compliant_candidate_fails_safe_without_reassigning(tmp_path):
    registry = SiteRegistry()
    cap = frozenset({"postgresql"})
    site_a = _trusted_site(registry, "site-a", region="r1", capabilities=cap)
    incapable_site = _trusted_site(registry, "site-c", region="r3", capabilities=frozenset())
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-a", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-c", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(site_a))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-c", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, _ = curate_regional_candidates([site_a, incapable_site], coord)
    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=candidates, plan_reference="plan-1",
        capability_requirement=CapabilityRequirement(required_capabilities=cap, plan_reference="plan-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        new_claim_factory=lambda site: _claim_for(site),
    )
    assert result.outcome == FailoverOutcome.NO_COMPLIANT_CANDIDATE
    assert result.new_record is None
    # Old owner IS fenced (site-a confirmed failed) even though no replacement exists --
    # matches "fail/pause safely", never "keep the stale owner alive because no
    # replacement was found".
    with pytest.raises(Exception):
        om.validate(old.ownership_key, old.lease_id, old.fencing_generation)


# ----------------------------------------------------------------------
# MANDATORY: sovereignty survives failover, end-to-end through ownership
# ----------------------------------------------------------------------

def test_mandatory_india_only_failover_rejects_singapore_end_to_end(tmp_path):
    """
    Full P7B.28 proof: India-only migration owns execution at Mumbai -> Mumbai fails ->
    Singapore is healthy/capable/reachable/cheaper -> Singapore MUST be rejected by
    residency -> zero compliant placement -> old (Mumbai) ownership is fenced (site
    confirmed failed) but NO new ownership is granted to Singapore. The correct terminal
    state is "no active owner", never "Singapore takes over".
    """
    registry = SiteRegistry()
    cap = frozenset({"postgresql"})
    mumbai = _trusted_site(registry, "site-mumbai", region="ap-south-1", capabilities=cap)
    singapore = _trusted_site(registry, "site-singapore", region="ap-southeast-1", capabilities=cap)
    coord = SiteCoordinator(registry, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-mumbai", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=1, reported_health=SiteHealthState.HEALTHY))

    om = OwnershipManager(site_registry=registry, fencing_manager=_fencing_manager(tmp_path))
    old = om.acquire(_claim_for(mumbai, migration_id="mig-india-1", plan_id="plan-india-1"))

    time.sleep(0.12)  # Mumbai fails
    coord.record_heartbeat(SiteHeartbeat(site_id="site-singapore", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, health = curate_regional_candidates([mumbai, singapore], coord)
    assert [c.site_id for c in candidates] == ["site-singapore"]

    result = attempt_failover(
        site_coordinator=coord, ownership_manager=om, old_ownership_key=old.ownership_key,
        candidates=candidates, plan_reference="plan-india-1",
        capability_requirement=CapabilityRequirement(required_capabilities=cap, plan_reference="plan-india-1"),
        authorization_action="execute", authorization_callback=lambda *a: True,
        residency_policies=(_india_only_policy(),),
        locality_by_site={"site-singapore": {LocalitySubjectRole.EXECUTION_SITE: _proven_country("site-singapore", "tenant-a", "SG")}},
        tenant_id="tenant-a",
        new_claim_factory=lambda site: _claim_for(site, migration_id="mig-india-1", plan_id="plan-india-1"),
    )

    assert result.outcome == FailoverOutcome.NO_COMPLIANT_CANDIDATE
    assert result.new_record is None
    assert result.selected_site_id is None

    # Mumbai's old ownership is fenced (confirmed failed) -- but Singapore never acquired
    # anything. Zero active owners is the correct, safe terminal state.
    with pytest.raises(Exception):
        om.validate(old.ownership_key, old.lease_id, old.fencing_generation)
    singapore_key = old.ownership_key  # same (tenant, migration, plan) unit of work
    assert om.try_get(singapore_key).site_id == "site-mumbai"  # no record was ever created for Singapore
    assert om.try_get(singapore_key).state.value == "FENCED"
