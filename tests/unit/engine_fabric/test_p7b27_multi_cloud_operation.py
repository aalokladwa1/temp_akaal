"""
tests.unit.engine_fabric.test_p7b27_multi_cloud_operation
==============================================================
P7B.27 -- Multi-Cloud Operation hostile test suite.

Proves cloud_identity_of/compute_cloud_health/curate_cross_cloud_candidates (composed
strictly over the frozen P7B.1 EnvironmentRegistry + P7B.24 SiteCoordinator, no duplicate
cloud-identity or placement authority) enforce:
    * cloud identity is resolved ONLY from the site's registered Environment, never from a
      caller-supplied label
    * two different AWS accounts (or Azure subscriptions, GCP projects, OCI tenancies) are
      never conflated into one cloud bucket merely by sharing an environment_type
    * a failed cloud can be excluded from candidacy without individually staling every one
      of its sites
    * cross-cloud residency (CLOUD_PROVIDER dimension) composes correctly through the
      UNMODIFIED Group-2 evaluate_candidates, exactly like P7B.26's region-based proof
"""

from __future__ import annotations

import time

import pytest

from akaalEngine.fabric.environment import AWSBoundary, AzureBoundary, Environment, EnvironmentRegistry, EnvironmentType
from akaalEngine.fabric.environment.registry import UnknownEnvironmentError
from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.execution_site.models import SiteHealthState
from akaalEngine.fabric.locality.models import LocalityConfidence, LocalityDimension, LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.multi_cloud import (
    CloudIdentity,
    CloudOperationalState,
    cloud_identity_of,
    compute_cloud_health,
    curate_cross_cloud_candidates,
)
from akaalEngine.fabric.placement.capability import CapabilityRequirement
from akaalEngine.fabric.placement.engine import evaluate_candidates
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.site_coordination import SiteCoordinator, SiteHeartbeat


def _env_registry_with(*envs):
    reg = EnvironmentRegistry()
    for env in envs:
        reg.register(env)
    return reg


def _aws_env(env_id, account_id):
    return Environment(environment_id=env_id, environment_type=EnvironmentType.AWS, boundary=AWSBoundary(account_id))


def _azure_env(env_id, subscription_id):
    return Environment(environment_id=env_id, environment_type=EnvironmentType.AZURE, boundary=AzureBoundary(subscription_id))


def _trusted_site(site_registry, site_id, environment_id, tenant_id="tenant-a", capabilities=frozenset()):
    site_registry.register(ExecutionSite(
        site_id=site_id, site_kind=SiteKind.CLOUD_VM, environment_id=environment_id,
        claimed_security_identity=f"spiffe://akaal.local/site/{site_id}", capabilities=capabilities,
    ))
    site_registry.verify_identity(site_id, verifier=lambda s, c: True, presented_credential="cert")
    site_registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    site_registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return site_registry.get(site_id)


AZURE_SUB_A = "11111111-1111-1111-1111-111111111111"
AZURE_SUB_B = "22222222-2222-2222-2222-222222222222"


# ----------------------------------------------------------------------
# Cloud identity resolution
# ----------------------------------------------------------------------

def test_cloud_identity_resolved_only_from_environment_never_from_site_id():
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"))
    sites = SiteRegistry()
    site = _trusted_site(sites, "definitely-not-aws-sounding-name", "env-aws-1")
    identity = cloud_identity_of(site, envs)
    assert identity.environment_type == "AWS"
    assert identity.native_boundary_key == ("AWS", "123456789012") or "123456789012" in identity.native_boundary_key


def test_two_different_aws_accounts_are_never_conflated():
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"), _aws_env("env-aws-2", "999999999999"))
    sites = SiteRegistry()
    site_a = _trusted_site(sites, "site-a", "env-aws-1")
    site_b = _trusted_site(sites, "site-b", "env-aws-2")
    id_a = cloud_identity_of(site_a, envs)
    id_b = cloud_identity_of(site_b, envs)
    assert id_a.as_key() != id_b.as_key()


def test_unknown_environment_fails_safe():
    envs = EnvironmentRegistry()
    sites = SiteRegistry()
    sites.register(ExecutionSite(site_id="orphan-site", site_kind=SiteKind.CLOUD_VM, environment_id="env-does-not-exist"))
    with pytest.raises(UnknownEnvironmentError):
        cloud_identity_of(sites.get("orphan-site"), envs)


# ----------------------------------------------------------------------
# Cloud health rollup
# ----------------------------------------------------------------------

def test_cloud_health_unavailable_when_all_sites_in_that_cloud_stale():
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"))
    sites = SiteRegistry()
    site = _trusted_site(sites, "site-1", "env-aws-1")
    coord = SiteCoordinator(sites, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-1", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    health = compute_cloud_health([site], coord, envs)
    identity = cloud_identity_of(site, envs)
    assert health[identity.as_key()].state == CloudOperationalState.UNAVAILABLE


def test_cloud_health_independent_per_account_even_with_same_environment_type():
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"), _aws_env("env-aws-2", "999999999999"))
    sites = SiteRegistry()
    healthy_site = _trusted_site(sites, "site-healthy", "env-aws-1")
    stale_site = _trusted_site(sites, "site-stale", "env-aws-2")
    coord = SiteCoordinator(sites, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-healthy", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-stale", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-healthy", sequence=2, reported_health=SiteHealthState.HEALTHY))

    health = compute_cloud_health([healthy_site, stale_site], coord, envs)
    assert health[cloud_identity_of(healthy_site, envs).as_key()].state == CloudOperationalState.HEALTHY
    assert health[cloud_identity_of(stale_site, envs).as_key()].state == CloudOperationalState.UNAVAILABLE


# ----------------------------------------------------------------------
# Cross-cloud candidate curation
# ----------------------------------------------------------------------

def test_curate_excludes_explicitly_failed_cloud_account():
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"), _azure_env("env-azure-1", AZURE_SUB_A))
    sites = SiteRegistry()
    aws_site = _trusted_site(sites, "site-aws", "env-aws-1")
    azure_site = _trusted_site(sites, "site-azure", "env-azure-1")
    coord = SiteCoordinator(sites)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-aws", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-azure", sequence=1, reported_health=SiteHealthState.HEALTHY))

    failed_cloud = cloud_identity_of(aws_site, envs)
    candidates, _ = curate_cross_cloud_candidates([aws_site, azure_site], coord, envs, exclude_cloud_identities=(failed_cloud,))
    assert [c.site_id for c in candidates] == ["site-azure"]


def test_curate_does_not_exclude_a_different_account_of_the_same_provider_type():
    """Excluding one failed AWS account must never accidentally exclude a DIFFERENT,
    healthy AWS account -- proves native_boundary_key, not environment_type alone, drives
    exclusion."""
    envs = _env_registry_with(_aws_env("env-aws-failed", "123456789012"), _aws_env("env-aws-healthy", "999999999999"))
    sites = SiteRegistry()
    failed_site = _trusted_site(sites, "site-failed-account", "env-aws-failed")
    healthy_site = _trusted_site(sites, "site-healthy-account", "env-aws-healthy")
    coord = SiteCoordinator(sites)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-failed-account", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-healthy-account", sequence=1, reported_health=SiteHealthState.HEALTHY))

    failed_identity = cloud_identity_of(failed_site, envs)
    candidates, _ = curate_cross_cloud_candidates([failed_site, healthy_site], coord, envs, exclude_cloud_identities=(failed_identity,))
    assert [c.site_id for c in candidates] == ["site-healthy-account"]


# ----------------------------------------------------------------------
# Cross-cloud residency composition (same law as P7B.26, exercised cross-cloud)
# ----------------------------------------------------------------------

def test_cross_cloud_residency_rejects_disallowed_provider_after_failover():
    """An AWS-only residency policy: AWS site fails, Azure site is healthy/reachable, but
    must be rejected on the CLOUD_PROVIDER residency dimension -- proving the P7B.26
    'cost/reachability never overrides residency' law composes identically cross-cloud."""
    envs = _env_registry_with(_aws_env("env-aws-1", "123456789012"), _azure_env("env-azure-1", AZURE_SUB_A))
    sites = SiteRegistry()
    cap = frozenset({"blob-storage"})
    aws_site = _trusted_site(sites, "site-aws", "env-aws-1", capabilities=cap)
    azure_site = _trusted_site(sites, "site-azure", "env-azure-1", capabilities=cap)

    coord = SiteCoordinator(sites, staleness_threshold_seconds=0.05)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-aws", sequence=1, reported_health=SiteHealthState.HEALTHY))
    coord.record_heartbeat(SiteHeartbeat(site_id="site-azure", sequence=1, reported_health=SiteHealthState.HEALTHY))
    time.sleep(0.12)
    coord.record_heartbeat(SiteHeartbeat(site_id="site-azure", sequence=2, reported_health=SiteHealthState.HEALTHY))

    candidates, health = curate_cross_cloud_candidates([aws_site, azure_site], coord, envs)
    assert [c.site_id for c in candidates] == ["site-azure"]  # AWS excluded purely by liveness

    aws_only_policy = ResidencyPolicy(
        policy_id="aws-only", dimension=LocalityDimension.CLOUD_PROVIDER,
        allowed_values=frozenset({"AWS"}), required_roles=(LocalitySubjectRole.EXECUTION_SITE,),
    )
    azure_locality = LocalityRecord(
        subject_ref="site-azure", subject_role=LocalitySubjectRole.EXECUTION_SITE, tenant_id="tenant-a",
        cloud_provider="AZURE", confidence=LocalityConfidence.PROVEN, provenance_source="PROVIDER_DISCOVERY",
    )
    requirement = CapabilityRequirement(required_capabilities=cap, plan_reference="plan-aws-only-1")
    result = evaluate_candidates(
        plan_reference="plan-aws-only-1", candidates=candidates, capability_requirement=requirement,
        actor_context={}, authorization_action="execute", authorization_callback=lambda *a: True,
        residency_policies=(aws_only_policy,), locality_by_site={"site-azure": {LocalitySubjectRole.EXECUTION_SITE: azure_locality}},
        tenant_id="tenant-a",
    )
    assert not result.has_compliant_placement()
    assert result.rejected[0].stage == "RESIDENCY"
