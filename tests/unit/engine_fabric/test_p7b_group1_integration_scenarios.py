"""
tests.unit.engine_fabric.test_p7b_group1_integration_scenarios
===================================================================
P7B Group 1 end-to-end integration scenarios, proving the full conceptual chain coheres
across all ten subphases rather than each module only passing in isolation:

    Environment -> Execution Site (trust) -> Connectivity -> Reachability
        -> Route Planning -> Remote Execution Assignment

and several of the required hostile end-to-end scenarios (P7B Group-1 §18).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.fabric.environment import (
    AWSBoundary,
    AzureBoundary,
    Environment,
    EnvironmentRegistry,
    EnvironmentType,
    OnPremBoundary,
    new_environment_id,
)
from akaalEngine.fabric.execution_site import (
    ExecutionSite,
    SiteKind,
    SiteRegistry,
)
from akaalEngine.fabric.connectivity import ConnectivityClass, ConnectivityEdge, PrivacyAchieved, ReachabilityEvidence
from akaalEngine.fabric.reachability import ReachabilityProber, ReachabilityProbeResult, ReachabilityFailureReason
from akaalEngine.fabric.route_planning import NoRouteFoundError, RoutePlanner, RouteShape
from akaalEngine.fabric.remote_execution import (
    RemoteExecutionControlPlane,
    StaleAssignmentError,
    WrongTenantError,
    verify_assignment,
)
from akaalEngine.fabric.resource_identity import AWSResourceLocator, ResourceLocatorValidationError

SIGNING_KEY = b"integration-scenario-signing-key"


def test_scenario_onprem_source_to_cloud_target_via_trusted_relay():
    """Scenario 1 (§18): on-prem source -> on-prem execution site -> cloud target."""
    env_registry = EnvironmentRegistry()
    onprem_env = env_registry.register(Environment(
        environment_id=new_environment_id(EnvironmentType.ON_PREMISES),
        environment_type=EnvironmentType.ON_PREMISES,
        boundary=OnPremBoundary(organization_unit="mumbai-dc"),
        geography="IN",
    ))
    aws_env = env_registry.register(Environment(
        environment_id=new_environment_id(EnvironmentType.AWS),
        environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary(account_id="123456789012"),
        region="ap-south-1",
    ))

    site_registry = SiteRegistry()
    site_registry.register(ExecutionSite(
        site_id="site-mumbai-dc",
        site_kind=SiteKind.ON_PREM_VM,
        environment_id=onprem_env.environment_id,
        claimed_security_identity="spiffe://akaal.local/site/mumbai-dc",
    ))
    site_registry.verify_identity("site-mumbai-dc", verifier=lambda s, cred: True, presented_credential="mtls-cert")
    site_registry.elevate_to_trusted("site-mumbai-dc", authorization_callback=lambda s, a, c: True)
    site_registry.bind_tenant("site-mumbai-dc", "tenant-acme", authorization_callback=lambda s, a, c: True)

    edge_source_to_site = ConnectivityEdge(
        edge_id="edge-src-to-site", source_ref="oracle-mumbai-source", destination_ref="site-mumbai-dc",
        connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="edge-src-to-site", achieved_privacy=PrivacyAchieved.PRIVATE))
    edge_site_to_target = ConnectivityEdge(
        edge_id="edge-site-to-target", source_ref="site-mumbai-dc", destination_ref="aws-target-rds",
        connectivity_class=ConnectivityClass.PRIVATE_ENDPOINT, is_private=True,
    ).elevate_to_proven(ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="edge-site-to-target", achieved_privacy=PrivacyAchieved.PRIVATE))

    route = RoutePlanner().plan_route("oracle-mumbai-source", "aws-target-rds", [edge_source_to_site, edge_site_to_target])
    assert route.shape == RouteShape.RELAY
    assert route.is_usable()

    control_plane = RemoteExecutionControlPlane(site_registry)
    assignment = control_plane.issue_assignment(
        site_id="site-mumbai-dc", tenant_id="tenant-acme", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp-scenario1", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )
    verify_assignment(
        assignment, SIGNING_KEY, expected_tenant_id="tenant-acme", expected_plan_id="plan-1",
        expected_site_id="site-mumbai-dc", expected_seal_fingerprint="seal-fp-scenario1",
    )


def test_scenario_forged_remote_assignment_rejected_end_to_end():
    """Scenario 9 (§18): forged remote assignment."""
    site_registry = SiteRegistry()
    site_registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.KUBERNETES, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    site_registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    site_registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    site_registry.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)

    control_plane = RemoteExecutionControlPlane(site_registry)
    real_assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp-x", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )

    # Attacker attempts to escalate privileges by presenting a forged assignment claiming
    # a different (higher-fencing-epoch, different-plan) identity, signed with a guessed key.
    import dataclasses
    forged = dataclasses.replace(real_assignment, plan_id="plan-attacker", fencing_epoch=999, signature="0" * 64)

    with pytest.raises(Exception):
        verify_assignment(
            forged, SIGNING_KEY, expected_tenant_id="tenant-a", expected_plan_id="plan-attacker",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-x",
        )


def test_scenario_cross_tenant_resource_locator_attack_rejected():
    """Scenario 10 (§18): cross-tenant resource locator attack."""
    # Tenant A's environment registered under its own AWS account.
    env_registry = EnvironmentRegistry()
    tenant_a_env = env_registry.register(Environment(
        environment_id="env-tenant-a-aws",
        environment_type=EnvironmentType.AWS,
        boundary=AWSBoundary(account_id="111111111111"),
    ))

    # An attacker crafts a resource locator claiming to be in tenant A's account, but the
    # ARN's own account segment reveals it actually belongs to a different account --
    # construction itself refuses the inconsistent locator.
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(
            arn="arn:aws:s3:us-east-1:222222222222:bucket/stolen-data",
            account_id="111111111111",  # attacker claims tenant A's account
        )

    # Even a well-formed locator naming a different account is registrable as its own
    # distinct environment -- it can never silently be "claimed" as belonging to tenant A's
    # already-registered environment id.
    from akaalEngine.fabric.environment import DuplicateEnvironmentIdentityError
    with pytest.raises(DuplicateEnvironmentIdentityError):
        env_registry.register(Environment(
            environment_id="env-tenant-a-aws",  # same locator ID attacker reuses
            environment_type=EnvironmentType.AWS,
            boundary=AWSBoundary(account_id="222222222222"),  # different physical account
        ))


def test_scenario_source_reachable_target_unreachable_asymmetric_classified():
    """Scenario from §8: source reachable/target unreachable must be distinctly recorded,
    and route planning must not treat a broken segment as viable."""
    def fake_probe(host, port, timeout_seconds=5.0):
        if host == "source-host":
            return ReachabilityProbeResult(evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="UNBOUND"))
        return ReachabilityProbeResult(
            evidence=ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=False, bound_edge_id="UNBOUND"),
            failure_reason=ReachabilityFailureReason.CONNECTION_REFUSED,
        )

    prober = ReachabilityProber(tcp_probe=fake_probe)
    edge = ConnectivityEdge(edge_id="e1", source_ref="src", destination_ref="dst", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True)
    result = prober.probe_bidirectional(edge, "source-host", 443, "target-unreachable-host", 443)
    assert result.is_asymmetric

    broken_edge = result.edge  # elevated based on combined evidence -> PROVEN_FAILED (asymmetric)
    with pytest.raises(NoRouteFoundError):
        RoutePlanner().plan_route("src", "dst", [broken_edge])


def test_scenario_stale_replayed_assignment_after_expiry_window():
    site_registry = SiteRegistry()
    site_registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.BARE_METAL, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    site_registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    site_registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    site_registry.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)

    control_plane = RemoteExecutionControlPlane(site_registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True, ttl_minutes=5,
    )

    far_future = datetime.now(timezone.utc) + timedelta(hours=2)
    with pytest.raises(StaleAssignmentError):
        verify_assignment(
            assignment, SIGNING_KEY, expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp", now=far_future,
        )
