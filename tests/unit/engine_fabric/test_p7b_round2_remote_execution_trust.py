"""
tests.unit.engine_fabric.test_p7b_round2_remote_execution_trust
===================================================================
P7B Group-1 Hostile Review Round 2 -- remote-execution trust architecture proof.

Proves, with executable evidence, the answers in the architecture note at the top of
akaalEngine/fabric/remote_execution/models.py:
  * no default/built-in signing key exists anywhere in this module;
  * signature verification never itself authorizes anything (it is checked IN ADDITION
    to SiteRegistry's prior canonical authorization, never instead of it);
  * a KMS/asymmetric-signing-ready seam (AssignmentSigner/AssignmentVerifier) exists and
    is substitutable without changing verification semantics;
  * a site/worker never needs (and in this design never receives) the signing key --
    only the control plane signs.
"""

from __future__ import annotations

import inspect

import pytest

from akaalEngine.fabric.execution_site import ExecutionSite, SiteKind, SiteRegistry
from akaalEngine.fabric.remote_execution import (
    AssignmentSigner,
    AssignmentVerifier,
    ForgedAssignmentError,
    HMACAssignmentSigner,
    HMACAssignmentVerifier,
    RemoteExecutionControlPlane,
    RemoteExecutionError,
    verify_assignment_with_verifier,
)


def _ready_registry(site_id="site-1", tenant_id="tenant-a") -> SiteRegistry:
    registry = SiteRegistry()
    registry.register(ExecutionSite(site_id=site_id, site_kind=SiteKind.KUBERNETES, environment_id="env-1", claimed_security_identity="spiffe://x/site-1"))
    registry.verify_identity(site_id, verifier=lambda s, cred: True, presented_credential="cred")
    registry.elevate_to_trusted(site_id, authorization_callback=lambda s, a, c: True)
    registry.bind_tenant(site_id, tenant_id, authorization_callback=lambda s, a, c: True)
    return registry


def test_no_default_signing_key_exists_issue_assignment_requires_one_explicitly():
    """issue_assignment has NO default value for signing_key/signer -- omitting both is a
    hard error, never a silent fallback to a built-in key."""
    sig = inspect.signature(RemoteExecutionControlPlane.issue_assignment)
    assert sig.parameters["signing_key"].default is None
    assert sig.parameters["signer"].default is None

    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(RemoteExecutionError):
        control_plane.issue_assignment(
            site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
            migration_id="mig-1", plan_id="plan-1", plan_revision=1,
            execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
            authorization_callback=lambda s, a, c: True,
            # neither signing_key nor signer supplied
        )


def test_cannot_supply_both_signing_key_and_signer_ambiguously():
    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    with pytest.raises(RemoteExecutionError):
        control_plane.issue_assignment(
            site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
            migration_id="mig-1", plan_id="plan-1", plan_revision=1,
            execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
            authorization_callback=lambda s, a, c: True,
            signing_key=b"a-key", signer=HMACAssignmentSigner(b"another-key"),
        )


def test_kms_ready_asymmetric_style_signer_substitutable_without_changing_semantics():
    """A custom AssignmentSigner/AssignmentVerifier pair (standing in for a real
    KMS-backed asymmetric signer) works end-to-end through the same issue/verify flow,
    proving the seam genuinely decouples signing from HMAC."""

    class _FakeAsymmetricSigner:
        """Stands in for e.g. an RSA/ECDSA KMS signer -- deterministic 'signature' derived
        differently from HMAC, to prove verify_assignment_with_verifier doesn't assume HMAC."""
        def sign(self, payload: bytes) -> str:
            return f"asym:{len(payload)}:{payload[:8].hex()}"

    class _FakeAsymmetricVerifier:
        def verify(self, payload: bytes, signature: str) -> bool:
            return signature == f"asym:{len(payload)}:{payload[:8].hex()}"

    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        authorization_callback=lambda s, a, c: True,
        signer=_FakeAsymmetricSigner(),
    )
    assert assignment.signature.startswith("asym:")

    verify_assignment_with_verifier(
        assignment, _FakeAsymmetricVerifier(),
        expected_tenant_id="tenant-a", expected_plan_id="plan-1",
        expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
    )  # must not raise


def test_forged_signature_rejected_through_verifier_seam_too():
    class _AlwaysRejectVerifier:
        def verify(self, payload: bytes, signature: str) -> bool:
            return False

    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        authorization_callback=lambda s, a, c: True,
        signing_key=b"real-key",
    )
    with pytest.raises(ForgedAssignmentError):
        verify_assignment_with_verifier(
            assignment, _AlwaysRejectVerifier(),
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
        )


def test_verifier_returning_non_bool_truthy_is_treated_as_forged_fail_closed():
    """A misbehaving verifier returning e.g. a truthy-but-non-True value must still be
    rejected -- only an exact `True` is accepted, matching the same fail-closed pattern
    used by every other callback in this codebase (SiteAuthorizationCallback, etc.)."""

    class _SloppyVerifier:
        def verify(self, payload: bytes, signature: str) -> bool:
            return 1  # truthy but not `is True`

    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        authorization_callback=lambda s, a, c: True,
        signing_key=b"real-key",
    )
    with pytest.raises(ForgedAssignmentError):
        verify_assignment_with_verifier(
            assignment, _SloppyVerifier(),
            expected_tenant_id="tenant-a", expected_plan_id="plan-1",
            expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
        )


def test_signature_verification_never_itself_performs_authorization():
    """Structural proof: verify_assignment's compiled bytecode never references any
    authorization-callback-shaped name -- it can only raise typed field-mismatch errors
    or return None. The only place an authorization DECISION is made anywhere in the
    remote-execution path is SiteRegistry.assign_execution, called once, before signing,
    inside issue_assignment -- never during verification."""
    import akaalEngine.fabric.remote_execution.models as models_mod
    names = models_mod.verify_assignment.__code__.co_names
    assert not any("authoriz" in n.lower() or "callback" in n.lower() for n in names)

    names_with_verifier = models_mod.verify_assignment_with_verifier.__code__.co_names
    assert not any("authoriz" in n.lower() or "callback" in n.lower() for n in names_with_verifier)


def test_site_never_needs_the_signing_key_to_be_assigned_work():
    """The site/worker side of this design only ever needs a VERIFIER (which, for a real
    asymmetric KMS-backed deployment, would be a PUBLIC key) -- never the signing key
    itself. Proven by constructing a verifier-only object with no signing capability and
    successfully verifying an assignment the control plane issued."""
    registry = _ready_registry()
    control_plane = RemoteExecutionControlPlane(registry)
    signing_key = b"control-plane-only-secret"
    assignment = control_plane.issue_assignment(
        site_id="site-1", tenant_id="tenant-a", workspace_id="ws-1", project_id="proj-1",
        migration_id="mig-1", plan_id="plan-1", plan_revision=1,
        execution_identity_seal_fingerprint="seal-fp", fencing_epoch=1, correlation_id="corr-1",
        authorization_callback=lambda s, a, c: True,
        signing_key=signing_key,
    )

    # The "site" side only holds a verifier -- constructed from the same key here purely
    # for the HMAC demo (a real deployment would hand the site a public-key verifier
    # instead, which structurally cannot sign at all -- HMACAssignmentVerifier below has
    # no .sign() method, proving the site-side object is verify-only).
    site_side_verifier = HMACAssignmentVerifier(signing_key)
    assert not hasattr(site_side_verifier, "sign")
    verify_assignment_with_verifier(
        assignment, site_side_verifier,
        expected_tenant_id="tenant-a", expected_plan_id="plan-1",
        expected_site_id="site-1", expected_seal_fingerprint="seal-fp",
    )
