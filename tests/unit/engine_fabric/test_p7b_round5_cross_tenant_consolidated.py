"""
tests.unit.engine_fabric.test_p7b_round5_cross_tenant_consolidated
=======================================================================
P7B Group-1 Hostile Closure Round 5 -- consolidated cross-tenant attack across every
Group-1 locator in one place (individual pieces were proven across Rounds 1-4; this
file ties them together as a single, explicit audit trail rather than requiring the
reader to reassemble it from many files).

For each locator type: possession of the locator string/id alone must never grant
membership, read access, planning eligibility, assignment, or execution across a tenant
boundary.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.environment import AWSBoundary, DuplicateEnvironmentIdentityError, Environment, EnvironmentRegistry, EnvironmentType
from akaalEngine.fabric.execution_site import ExecutionSite, SiteIdentityCollisionError, SiteKind, SiteRegistry, SiteRegistryError
from akaalEngine.fabric.resource_identity import AWSResourceLocator, ResourceLocatorValidationError
from akaalEngine.fabric.connectivity import ConnectivityClass, ConnectivityEdge, PrivacyAchieved, ReachabilityEvidence, ConnectivityValidationError
from akaalEngine.fabric.route_planning import NoRouteFoundError, RoutePlanner
from akaalEngine.fabric.remote_execution import RemoteExecutionControlPlane, WrongTenantError, verify_assignment

SIGNING_KEY = b"cross-tenant-consolidated-key-01"


def test_environment_id_possession_does_not_grant_cross_tenant_registration():
    registry = EnvironmentRegistry()
    registry.register(Environment(environment_id="env-shared", environment_type=EnvironmentType.AWS, boundary=AWSBoundary("111111111111")))
    with pytest.raises(DuplicateEnvironmentIdentityError):
        registry.register(Environment(environment_id="env-shared", environment_type=EnvironmentType.AWS, boundary=AWSBoundary("222222222222")))


def test_resource_locator_possession_does_not_grant_cross_account_claim():
    with pytest.raises(ResourceLocatorValidationError):
        AWSResourceLocator(arn="arn:aws:s3:us-east-1:222222222222:bucket/victim-bucket", account_id="111111111111")


def test_site_id_possession_does_not_grant_cross_environment_hijack():
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-shared", site_kind=SiteKind.CLOUD_VM, environment_id="env-tenant-a", claimed_security_identity="spiffe://x/real"))
    with pytest.raises(SiteIdentityCollisionError):
        registry.register(ExecutionSite(site_id="site-shared", site_kind=SiteKind.CLOUD_VM, environment_id="env-attacker", claimed_security_identity="spiffe://x/attacker"))


def test_connectivity_edge_id_possession_does_not_grant_evidence_substitution():
    edge_a = ConnectivityEdge(edge_id="edge-tenant-a", source_ref="a-src", destination_ref="a-dst", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True)
    forged_evidence = ReachabilityEvidence(probe_method="TCP_CONNECT", succeeded=True, bound_edge_id="edge-tenant-b", achieved_privacy=PrivacyAchieved.PRIVATE)
    with pytest.raises(ConnectivityValidationError):
        edge_a.elevate_to_proven(forged_evidence)


def test_route_planning_cannot_be_forced_across_tenant_via_edge_authorization_filter():
    edge = ConnectivityEdge(edge_id="e1", source_ref="tenant-a-src", destination_ref="tenant-b-dst", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True)

    def tenant_scoped_authorization(candidate_edge, context):
        return False  # simulates: this edge crosses a tenant boundary the caller may not use

    with pytest.raises(NoRouteFoundError):
        RoutePlanner().plan_route("tenant-a-src", "tenant-b-dst", [edge], authorization_callback=tenant_scoped_authorization)


def test_assignment_id_possession_does_not_grant_cross_tenant_verification():
    site_registry = SiteRegistry()
    site_registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.CLOUD_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    site_registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    site_registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    site_registry.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)

    control_plane = RemoteExecutionControlPlane(site_registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        signing_key=SIGNING_KEY, authorization_callback=lambda s, a, c: True,
    )
    # An attacker who obtained the assignment_id/object alone but claims a different
    # tenant when verifying is still rejected -- the tenant check is on signed content,
    # not on whether the caller "has" the assignment.
    with pytest.raises(WrongTenantError):
        verify_assignment(
            assignment, SIGNING_KEY, expected_tenant_id="tenant-attacker",
            expected_plan_id="plan-1", expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
        )


def test_secret_reference_string_possession_does_not_resolve_without_correct_provider_scope():
    from akaalEngine.connection.security.providers.aws_secrets_manager import AWSSecretsManagerConfig, AWSSecretsManagerError, AWSSecretsManagerProvider

    class _FakeClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": "value", "ARN": "arn:aws:secretsmanager:us-east-1:222222222222:secret:x"}

    provider = AWSSecretsManagerProvider(AWSSecretsManagerConfig(account_id="111111111111"), client=_FakeClient())
    with pytest.raises(AWSSecretsManagerError):
        provider.resolve("x")  # knowing the secret name alone doesn't cross the account boundary


def test_cloud_identity_possession_does_not_grant_akaal_authorization_for_another_tenant():
    from akaalEngine.fabric.workload_identity import CloudAuthenticationBoundary, CloudAuthProvider, CloudIdentityContext
    from datetime import datetime, timedelta, timezone

    identity = CloudIdentityContext(
        provider=CloudAuthProvider.AWS, principal_id="arn:aws:sts::123456789012:assumed-role/akaal/x",
        account_boundary="123456789012", expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )
    boundary = CloudAuthenticationBoundary()

    def tenant_scoped_callback(ident, action, context):
        return context.get("tenant_id") == "tenant-a"

    assert boundary.authorize_akaal_action(identity, "read", tenant_scoped_callback, context={"tenant_id": "tenant-attacker"}) is False


def test_staging_reference_possession_does_not_bypass_route_tenant_authorization():
    """A staging identity string appearing in a route's hop list is subject to the exact
    same authorization_callback filtering as any other edge -- there is no special
    'staging bypasses tenant checks' path."""
    edge_to_staging = ConnectivityEdge(edge_id="e-to-staging", source_ref="src", destination_ref="shared-staging-bucket", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True)
    edge_from_staging = ConnectivityEdge(edge_id="e-from-staging", source_ref="shared-staging-bucket", destination_ref="dst", connectivity_class=ConnectivityClass.DIRECT_PRIVATE, is_private=True)

    def deny_staging_for_this_tenant(candidate_edge, context):
        return "staging" not in candidate_edge.destination_ref and "staging" not in candidate_edge.source_ref

    with pytest.raises(NoRouteFoundError):
        RoutePlanner().plan_route("src", "dst", [edge_to_staging, edge_from_staging], staging_ref="shared-staging-bucket", authorization_callback=deny_staging_for_this_tenant)
