"""
tests.unit.engine_fabric.test_p7b_5_execution_site
======================================================
P7B.5 hostile tests -- execution site trust & registration.

Proves: SITE REGISTRATION != SITE TRUST != SITE AUTHORIZATION. A site cannot self-grant
tenant access, migration assignment, capabilities, or trusted status. Stale/replayed
fencing must not execute. Cross-tenant assignment refused.
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.execution_site import (
    AssignmentAuthorizationDeniedError,
    ExecutionSite,
    SiteAssignment,
    SiteKind,
    SiteRegistry,
    SiteRegistryError,
    SiteSelfElevationRejectedError,
    SiteTrustState,
    StaleFencingError,
    UnknownSiteError,
)


def _site(site_id="site-1", trust_state=SiteTrustState.UNREGISTERED, claimed_identity="spiffe://akaal.local/site/site-1"):
    return ExecutionSite(
        site_id=site_id,
        site_kind=SiteKind.ON_PREM_VM,
        environment_id="env-onprem-1",
        claimed_security_identity=claimed_identity,
        trust_state=trust_state,
    )


def test_site_cannot_self_register_as_already_trusted():
    registry = SiteRegistry()
    with pytest.raises(SiteSelfElevationRejectedError):
        registry.register(_site(trust_state=SiteTrustState.TRUSTED))


def test_registration_never_elevates_trust_beyond_registered():
    registry = SiteRegistry()
    registered = registry.register(_site())
    assert registered.trust_state == SiteTrustState.REGISTERED
    assert registered.tenant_binding is None


def test_unknown_site_fails_safely():
    registry = SiteRegistry()
    with pytest.raises(UnknownSiteError):
        registry.get("site-does-not-exist")


def test_trust_elevation_requires_identity_verification_first():
    registry = SiteRegistry()
    registry.register(_site())
    with pytest.raises(SiteRegistryError):
        registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)


def test_identity_verification_rejects_false_verifier_result():
    registry = SiteRegistry()
    registry.register(_site())
    with pytest.raises(SiteRegistryError):
        registry.verify_identity("site-1", verifier=lambda s, cred: False, presented_credential="bad-cred")


def test_trust_elevation_without_authorization_callback_fails_closed():
    registry = SiteRegistry()
    registry.register(_site())
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert-bytes")
    with pytest.raises(SiteRegistryError):
        registry.elevate_to_trusted("site-1", authorization_callback=None)


def test_trust_elevation_denied_by_callback_is_respected():
    registry = SiteRegistry()
    registry.register(_site())
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert-bytes")
    with pytest.raises(AssignmentAuthorizationDeniedError):
        registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: False)


def _fully_trusted_and_bound(registry: SiteRegistry, tenant_id="tenant-a") -> ExecutionSite:
    registry.register(_site())
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert-bytes")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    return registry.bind_tenant("site-1", tenant_id, authorization_callback=lambda s, a, c: True)


def test_tenant_binding_requires_trusted_state():
    registry = SiteRegistry()
    registry.register(_site())
    with pytest.raises(SiteRegistryError):
        registry.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)


def test_tenant_binding_without_callback_fails_closed():
    registry = SiteRegistry()
    registry.register(_site())
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cert-bytes")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    with pytest.raises(SiteRegistryError):
        registry.bind_tenant("site-1", "tenant-a", authorization_callback=None)


def test_execution_assignment_before_readiness_rejected():
    registry = SiteRegistry()
    registry.register(_site())
    assignment = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=1)
    with pytest.raises(SiteRegistryError):
        registry.assign_execution(assignment, authorization_callback=lambda s, a, c: True)


def test_execution_assignment_cross_tenant_rejected():
    registry = SiteRegistry()
    _fully_trusted_and_bound(registry, tenant_id="tenant-a")
    assignment = SiteAssignment(site_id="site-1", tenant_id="tenant-b", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=1)
    with pytest.raises(SiteRegistryError):
        registry.assign_execution(assignment, authorization_callback=lambda s, a, c: True)


def test_execution_assignment_without_callback_fails_closed_ie_site_cannot_self_assign():
    registry = SiteRegistry()
    _fully_trusted_and_bound(registry, tenant_id="tenant-a")
    assignment = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=1)
    with pytest.raises(SiteRegistryError):
        registry.assign_execution(assignment, authorization_callback=None)


def test_execution_assignment_succeeds_with_valid_epoch_and_authorization():
    registry = SiteRegistry()
    _fully_trusted_and_bound(registry, tenant_id="tenant-a")
    assignment = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=1)
    result = registry.assign_execution(assignment, authorization_callback=lambda s, a, c: True)
    assert result.fencing_epoch == 1


def test_stale_fencing_epoch_rejected_after_higher_epoch_recorded():
    """Stale fencing must not execute -- even with valid trust/tenant/authorization."""
    registry = SiteRegistry()
    _fully_trusted_and_bound(registry, tenant_id="tenant-a")

    first = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=5)
    registry.assign_execution(first, authorization_callback=lambda s, a, c: True)

    replayed = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=5)
    with pytest.raises(StaleFencingError):
        registry.assign_execution(replayed, authorization_callback=lambda s, a, c: True)

    lower = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=3)
    with pytest.raises(StaleFencingError):
        registry.assign_execution(lower, authorization_callback=lambda s, a, c: True)

    higher = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=6)
    registry.assign_execution(higher, authorization_callback=lambda s, a, c: True)  # must succeed


def test_revocation_always_permitted_without_callback_and_blocks_further_assignment():
    registry = SiteRegistry()
    _fully_trusted_and_bound(registry, tenant_id="tenant-a")
    revoked = registry.revoke("site-1", reason="compromised host detected")
    assert revoked.trust_state == SiteTrustState.REVOKED

    assignment = SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=1)
    with pytest.raises(SiteRegistryError):
        registry.assign_execution(assignment, authorization_callback=lambda s, a, c: True)


def test_revocation_requires_nonempty_reason():
    registry = SiteRegistry()
    registry.register(_site())
    with pytest.raises(SiteRegistryError):
        registry.revoke("site-1", reason="")


def test_malformed_site_assignment_rejected():
    with pytest.raises(Exception):
        SiteAssignment(site_id="", tenant_id="t", workspace_id="w", migration_id="m", plan_id="p", fencing_epoch=1)
    with pytest.raises(Exception):
        SiteAssignment(site_id="s", tenant_id="t", workspace_id="w", migration_id="m", plan_id="p", fencing_epoch=0)


def test_kubernetes_is_one_implementation_not_a_universal_requirement():
    """Every SiteKind is a first-class, independently constructible Execution Site --
    Kubernetes carries no special-cased requirement anywhere in the model."""
    for kind in SiteKind:
        site = ExecutionSite(site_id=f"site-{kind.value.lower()}", site_kind=kind, environment_id="env-1")
        assert site.site_kind == kind
