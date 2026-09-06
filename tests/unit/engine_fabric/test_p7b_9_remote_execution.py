"""
tests.unit.engine_fabric.test_p7b_9_remote_execution
========================================================
P7B.9 hostile tests -- hybrid relay / remote execution.

Proves: forged assignments rejected; stale/expired assignments rejected; replay (reused
fencing epoch) rejected at the SiteRegistry layer (reused, not re-implemented here);
wrong plan/tenant/seal/site all rejected distinctly; a site cannot self-assign (issuance
requires SiteRegistry authorization); remote execution never invents its own plan/tenant.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from akaalEngine.fabric.execution_site import (
    AssignmentAuthorizationDeniedError,
    ExecutionSite,
    SiteKind,
    SiteRegistry,
    SiteRegistryError,
    UnknownSiteError,
)
from akaalEngine.fabric.remote_execution import (
    ForgedAssignmentError,
    RemoteExecutionControlPlane,
    RemoteExecutionError,
    StaleAssignmentError,
    WrongPlanError,
    WrongSealError,
    WrongSiteError,
    WrongTenantError,
    verify_assignment,
)

SIGNING_KEY = b"test-signing-key-not-for-production"


def _ready_site_registry(site_id="site-1", tenant_id="tenant-a") -> SiteRegistry:
    registry = SiteRegistry()
    registry.register(ExecutionSite(
        site_id=site_id,
        site_kind=SiteKind.ON_PREM_VM,
        environment_id="env-1",
        claimed_security_identity="spiffe://akaal.local/site/site-1",
    ))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cert")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def _issue(control_plane, **overrides):
    defaults = dict(
        site_id="site-1",
        tenant_id="tenant-a",
        workspace_id="ws-1",
        project_id="proj-1",
        migration_id="mig-1",
        plan_id="plan-1",
        plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp-abc123",
        fencing_epoch=1,
        correlation_id="corr-1",
        signing_key=SIGNING_KEY,
        authorization_callback=lambda s, a, c: True,
    )
    defaults.update(overrides)
    return control_plane.issue_assignment(**defaults)


def test_site_cannot_self_assign_issuance_requires_site_registry_authorization():
    registry = SiteRegistry()  # not registered/trusted/bound at all
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(UnknownSiteError):
        _issue(control_plane)


def test_issuance_denied_by_site_authorization_callback_is_respected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(AssignmentAuthorizationDeniedError):
        _issue(control_plane, authorization_callback=lambda s, a, c: False)


def test_valid_assignment_verifies_successfully():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    verify_assignment(
        assignment,
        SIGNING_KEY,
        expected_tenant_id="tenant-a",
        expected_plan_id="plan-1",
        expected_site_id="site-1",
        expected_seal_fingerprint="seal-fp-abc123",
    )  # must not raise


def test_forged_signature_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)

    import dataclasses
    forged = dataclasses.replace(assignment, plan_id="plan-attacker-substituted")

    with pytest.raises(ForgedAssignmentError):
        verify_assignment(
            forged, SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-attacker-substituted",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
        )


def test_wrong_signing_key_rejected_as_forged():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    with pytest.raises(ForgedAssignmentError):
        verify_assignment(
            assignment, b"attacker-guessed-key",
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
        )


def test_stale_expired_assignment_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane, ttl_minutes=0.001) if False else _issue(control_plane)
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    with pytest.raises(StaleAssignmentError):
        verify_assignment(
            assignment, SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
            now=future,
        )


def test_replayed_fencing_epoch_rejected_by_reused_site_registry_logic():
    """Replay must not create authority -- reissuing an assignment at the same epoch is
    rejected by SiteRegistry.assign_execution (P7B.5), which this control plane reuses
    rather than re-implementing."""
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    _issue(control_plane, fencing_epoch=3)
    from akaalEngine.fabric.execution_site import StaleFencingError
    with pytest.raises(StaleFencingError):
        _issue(control_plane, fencing_epoch=3)  # exact replay
    with pytest.raises(StaleFencingError):
        _issue(control_plane, fencing_epoch=2)  # lower epoch


def test_wrong_plan_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    with pytest.raises(WrongPlanError):
        verify_assignment(
            assignment, SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-DIFFERENT",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
        )


def test_wrong_tenant_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    with pytest.raises(WrongTenantError):
        verify_assignment(
            assignment, SIGNING_KEY,
            expected_tenant_id="tenant-DIFFERENT", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
        )


def test_wrong_site_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    with pytest.raises(WrongSiteError):
        verify_assignment(
            assignment, SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-DIFFERENT", expected_seal_fingerprint="seal-fp-abc123",
        )


def test_wrong_seal_rejected():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = _issue(control_plane)
    with pytest.raises(WrongSealError):
        verify_assignment(
            assignment, SIGNING_KEY,
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp-DIFFERENT",
        )


def test_issuance_requires_nonempty_signing_key_and_seal_fingerprint():
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(RemoteExecutionError):
        _issue(control_plane, signing_key=b"")
    with pytest.raises(RemoteExecutionError):
        _issue(control_plane, execution_identity_seal_fingerprint="")


def test_cross_tenant_assignment_cannot_be_issued_for_unbound_tenant():
    """Even with a permissive authorization_callback, SiteRegistry itself refuses to bind
    an assignment to a tenant the site was never bound to -- reused fail-closed logic."""
    registry = _ready_site_registry(tenant_id="tenant-a")
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(SiteRegistryError):
        _issue(control_plane, tenant_id="tenant-b")


def test_disconnect_reconnect_reissue_at_higher_epoch_succeeds():
    """A legitimate disconnect/reconnect scenario: the control plane reissues at a
    strictly higher fencing epoch and it succeeds, proving stale rejection is about
    ordering, not blanket re-issuance denial."""
    registry = _ready_site_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    first = _issue(control_plane, fencing_epoch=1, correlation_id="corr-before-disconnect")
    second = _issue(control_plane, fencing_epoch=2, correlation_id="corr-after-reconnect")
    assert first.correlation_id != second.correlation_id
    verify_assignment(
        second, SIGNING_KEY,
        expected_tenant_id="tenant-a", expected_plan_id="plan-1",
        expected_site_id="site-1", expected_seal_fingerprint="seal-fp-abc123",
    )
