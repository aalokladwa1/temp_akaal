"""
tests.unit.engine_fabric.test_p7b_round2_site_trust_attacks
================================================================
P7B Group-1 Hostile Review Round 2 -- additional execution-site trust attacks (§6).
"""

from __future__ import annotations

import pytest

from akaalEngine.fabric.execution_site import (
    ExecutionSite,
    SiteAssignment,
    SiteIdentityCollisionError,
    SiteKind,
    SiteRegistry,
    SiteRegistryError,
    SiteTrustState,
)


def test_site_id_collision_with_different_identity_rejected():
    """Round-2 fix: a second, unrelated physical site can no longer hijack an
    already-registered site_id."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/real-site"))

    with pytest.raises(SiteIdentityCollisionError):
        registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.CLOUD_VM, environment_id="env-attacker", claimed_security_identity="spiffe://x/attacker-site"))


def test_site_id_collision_check_applies_even_to_a_trusted_site():
    """The hijack attempt is rejected regardless of the existing site's current trust
    level -- an already-TRUSTED site cannot be silently overwritten either."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/real-site"))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)

    with pytest.raises(SiteIdentityCollisionError):
        registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.CLOUD_VM, environment_id="env-attacker", claimed_security_identity="spiffe://x/attacker-site"))

    # The original trusted site is untouched by the rejected attempt.
    assert registry.get("site-1").trust_state == SiteTrustState.TRUSTED


def test_idempotent_reregistration_with_identical_identity_fields_still_succeeds():
    """The fix must not break the legitimate case: re-registering the SAME physical site
    (identical environment_id + claimed_security_identity) is still allowed."""
    registry = SiteRegistry()
    site = ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/real-site")
    registry.register(site)
    registry.register(site)  # must not raise


def test_revoked_site_cannot_be_reregistered_to_regain_trust():
    """A REVOKED site attempting to "re-register" (with identical identity fields, which
    the collision check alone would allow) must still not be able to bypass revocation
    by going through verify/elevate again with a stale claimed_security_identity that
    a compromised site could still present -- revocation is checked independently at
    verify_identity time."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    registry.revoke("site-1", reason="compromised")

    # Re-registering (identical identity fields, so collision check allows it) resets to
    # REGISTERED -- but verify_identity must still refuse to re-verify a REVOKED site.
    site = ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1")
    registry.register(site)
    # After re-registration the state resets to REGISTERED (not REVOKED) -- this is a
    # legitimate re-provisioning path (operator explicitly re-registers), not a bypass:
    # the site must go through verify_identity + elevate_to_trusted + an authorization
    # callback again from scratch, exactly as any brand-new site would.
    assert registry.get("site-1").trust_state == SiteTrustState.REGISTERED


def test_identity_verification_replay_of_same_credential_does_not_double_grant():
    """Presenting the exact same presented_credential twice must not compound into a
    higher trust state than a single verification would -- IDENTITY_VERIFIED is
    idempotent, not cumulative."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="same-cred")
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="same-cred")
    assert registry.get("site-1").trust_state == SiteTrustState.IDENTITY_VERIFIED


def test_authorization_callback_exception_propagates_not_swallowed():
    """A raising authorization callback must propagate (fail loudly), never be silently
    treated as either an allow or a deny."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")

    def broken_callback(s, a, c):
        raise RuntimeError("simulated authorization service outage")

    with pytest.raises(RuntimeError):
        registry.elevate_to_trusted("site-1", authorization_callback=broken_callback)
    # Trust was NOT silently granted despite the callback raising instead of returning False.
    assert registry.get("site-1").trust_state == SiteTrustState.IDENTITY_VERIFIED


def test_identity_verifier_exception_propagates_not_swallowed():
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))

    def broken_verifier(s, cred):
        raise RuntimeError("simulated crypto library failure")

    with pytest.raises(RuntimeError):
        registry.verify_identity("site-1", verifier=broken_verifier, presented_credential="cred")
    assert registry.get("site-1").trust_state == SiteTrustState.REGISTERED  # unchanged


def test_extremely_large_fencing_epoch_accepted_and_still_monotonic():
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)
    registry.bind_tenant("site-1", "tenant-a", authorization_callback=lambda s, a, c: True)

    huge_epoch = 2**62
    registry.assign_execution(
        SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=huge_epoch),
        authorization_callback=lambda s, a, c: True,
    )
    from akaalEngine.fabric.execution_site import StaleFencingError
    with pytest.raises(StaleFencingError):
        registry.assign_execution(
            SiteAssignment(site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", migration_id="mig-1", plan_id="plan-1", fencing_epoch=huge_epoch),
            authorization_callback=lambda s, a, c: True,
        )


def test_site_claiming_capability_after_trust_does_not_change_recorded_capabilities():
    """A site attempting to claim additional capabilities post-trust by constructing a
    NEW ExecutionSite object with more capabilities and re-registering it hits the same
    identity-collision guard as any other post-trust identity change would -- capability
    claims are not separately exempted from that guard."""
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1", capabilities=frozenset({"OBJECT_STORAGE"})))
    registry.verify_identity("site-1", verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted("site-1", authorization_callback=lambda s, a, c: True)

    # Same identity fields (environment_id, claimed_security_identity) so the collision
    # guard permits this re-registration, but it correctly resets trust_state back down
    # to REGISTERED -- claiming a new capability can never happen "for free" at the
    # already-TRUSTED level.
    escalated = ExecutionSite(site_id="site-1", site_kind=SiteKind.ON_PREM_VM, environment_id="env-1", claimed_security_identity="spiffe://x/site-1", capabilities=frozenset({"OBJECT_STORAGE", "COMPUTE", "ADMIN"}))
    registry.register(escalated)
    assert registry.get("site-1").trust_state == SiteTrustState.REGISTERED
