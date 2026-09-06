"""
akaalEngine.fabric.remote_execution.models
=============================================
P7B.9 -- Hybrid Relay / Remote Execution models.

A RemoteExecutionAssignment is a signed, fencing-bound, time-bounded authorization for
ONE canonical AKAAL runtime instance at ONE trusted execution site to perform ONE
already-planned unit of work. It is produced exclusively by
akaalEngine.fabric.remote_execution.control_plane.RemoteExecutionControlPlane (which
itself delegates trust/fencing to akaalEngine.fabric.execution_site.SiteRegistry -- never
re-implemented here), and it never:
    * invents or modifies a plan (it carries only a plan_id + plan_revision + an opaque
      seal fingerprint computed elsewhere, from the actual ExecutionPlan/ExecutionSeal --
      it never reconstructs plan content);
    * self-assigns (issuance always requires SiteRegistry.assign_execution's own
      authorization callback + fencing check to have already succeeded);
    * changes tenant/workspace/project (these are baked into the signed payload and
      verified on every read, never re-derived from the transport or the remote side).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------------
# Round-2 hostile-review architecture note (P7B Group-1 §5 -- "hostile review
# remote-execution trust"):
#
#   Who owns the signing key?            The CALLER (production: whatever holds
#                                         Pipeline's KMS/PKI custody -- see
#                                         akaalPipeline.security.kms_provider). This
#                                         module never generates, stores, or defaults
#                                         one -- `RemoteExecutionControlPlane.issue_assignment`
#                                         has no default value for its key/signer
#                                         parameter; omitting it is a hard TypeError,
#                                         not a fallback to a built-in key.
#   How is it obtained/rotated/scoped?   Entirely the caller's responsibility, via
#                                         whatever `AssignmentSigner`/`AssignmentVerifier`
#                                         implementation the caller supplies (see below) --
#                                         this module defines the *seam*, not the custody.
#   Can one tenant's key sign another
#   tenant's assignment?                 If a caller reuses one shared key across
#                                         tenants, yes the HMAC itself would validate --
#                                         exactly like any other shared-secret MAC/JWT
#                                         scheme. This module does NOT rely on
#                                         per-tenant key material for its tenant-scoping
#                                         guarantee: verify_assignment independently
#                                         checks tenant_id/plan_id/site_id/seal_fingerprint
#                                         as explicit fields (see verify_assignment).
#                                         Field-based scoping plus caller-side key
#                                         confidentiality is the actual security
#                                         boundary -- not "one key per tenant" (which
#                                         a caller MAY still choose to do for
#                                         defense-in-depth, but this module does not
#                                         assume it).
#   Can one site forge another site's
#   assignment, or can compromise of one
#   worker/site mint assignments?        No -- signing happens exclusively in
#                                         RemoteExecutionControlPlane.issue_assignment
#                                         (control plane side). A site/worker NEVER
#                                         holds the signing key; it only ever receives
#                                         the already-signed assignment and can verify
#                                         it (verification needs only the key/verifier,
#                                         which in a real KMS-backed deployment can be a
#                                         PUBLIC verification key via an asymmetric
#                                         AssignmentSigner/AssignmentVerifier pair --
#                                         HMAC is provided here only as the default,
#                                         symmetric, dev/test-friendly implementation).
#   Message integrity or authorization?  Message integrity/authenticity ONLY. Signature
#                                         verification (verify_assignment /
#                                         verify_assignment_with_verifier) NEVER performs
#                                         or replaces an authorization decision -- it
#                                         only proves "this assignment is exactly what
#                                         the control plane issued, untampered, not
#                                         expired, and matches the caller's expected
#                                         tenant/plan/site/seal". The actual AKAAL
#                                         authorization decision already happened, once,
#                                         inside SiteRegistry.assign_execution's
#                                         authorization_callback BEFORE the control plane
#                                         ever signs anything (see control_plane.py).
#                                         Signature verification is checked IN ADDITION
#                                         to that prior canonical authorization, never
#                                         instead of it -- there is no code path where
#                                         verify_assignment succeeding is treated as
#                                         itself granting anything.
#   Does this duplicate PKI/SPIFHE/KMS?  No new key-custody, certificate-issuance, or
#                                         identity-verification authority is created.
#                                         `AssignmentSigner`/`AssignmentVerifier` below
#                                         are pure Protocols (an integration seam only,
#                                         following the same pattern as
#                                         akaalEngine.fabric.workload_identity.boundary's
#                                         AKAALAuthorizationCallback and
#                                         akaalPipeline.security.kms_provider's own
#                                         KeyManagementProvider Protocol) -- production
#                                         deployments are expected to implement them by
#                                         wrapping Pipeline's KeyManagementProvider
#                                         (sign/verify), not by inventing new custody.
# ---------------------------------------------------------------------------------


class RemoteExecutionError(RuntimeError):
    pass


class ForgedAssignmentError(RemoteExecutionError):
    """Raised when an assignment's signature does not match its claimed content."""


class StaleAssignmentError(RemoteExecutionError):
    """Raised when an assignment has expired. Never silently extended."""


class WrongTenantError(RemoteExecutionError):
    pass


class WrongPlanError(RemoteExecutionError):
    pass


class WrongSealError(RemoteExecutionError):
    pass


class WrongSiteError(RemoteExecutionError):
    pass


def _canonical_payload(
    assignment_id: str,
    site_id: str,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
    migration_id: str,
    plan_id: str,
    plan_revision: int,
    execution_identity_seal_fingerprint: str,
    fencing_epoch: int,
    correlation_id: str,
    issued_at: str,
    expires_at: str,
) -> bytes:
    fields = {
        "assignment_id": assignment_id,
        "site_id": site_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "project_id": project_id,
        "migration_id": migration_id,
        "plan_id": plan_id,
        "plan_revision": plan_revision,
        "execution_identity_seal_fingerprint": execution_identity_seal_fingerprint,
        "fencing_epoch": fencing_epoch,
        "correlation_id": correlation_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class RemoteExecutionAssignment:
    """
    Immutable, signed remote execution assignment. Construct only via
    RemoteExecutionControlPlane.issue_assignment -- direct construction with a
    self-computed signature is possible in Python but is exactly the "forged assignment"
    hostile case verify_assignment() exists to catch.
    """
    assignment_id: str
    site_id: str
    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_revision: int
    execution_identity_seal_fingerprint: str
    fencing_epoch: int
    correlation_id: str
    signature: str
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat())

    def canonical_payload(self) -> bytes:
        return _canonical_payload(
            self.assignment_id, self.site_id, self.tenant_id, self.workspace_id, self.project_id,
            self.migration_id, self.plan_id, self.plan_revision, self.execution_identity_seal_fingerprint,
            self.fencing_epoch, self.correlation_id, self.issued_at, self.expires_at,
        )

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        current = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return current >= expiry


@runtime_checkable
class AssignmentSigner(Protocol):
    """Integration seam for real key custody (e.g. a caller-supplied wrapper around
    akaalPipeline.security.kms_provider.KeyManagementProvider.sign). This module's own
    HMACAssignmentSigner below is the default, symmetric, dev/test implementation --
    production deployments wanting asymmetric/KMS-backed signing implement this Protocol
    instead of passing raw key bytes."""

    def sign(self, payload: bytes) -> str: ...


@runtime_checkable
class AssignmentVerifier(Protocol):
    """Verification counterpart to AssignmentSigner. Must return False (never raise) for
    an invalid signature -- verify_assignment_with_verifier treats any non-True return as
    a forged/invalid assignment."""

    def verify(self, payload: bytes, signature: str) -> bool: ...


class HMACAssignmentSigner:
    """Default symmetric HMAC-SHA256 signer. The caller owns `key` entirely -- this
    class never generates, stores beyond the instance, or defaults one."""

    def __init__(self, key: bytes) -> None:
        if not key:
            raise RemoteExecutionError("HMACAssignmentSigner requires a non-empty key.")
        self._key = key

    def sign(self, payload: bytes) -> str:
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()


class HMACAssignmentVerifier:
    """Default symmetric HMAC-SHA256 verifier counterpart to HMACAssignmentSigner."""

    def __init__(self, key: bytes) -> None:
        if not key:
            raise RemoteExecutionError("HMACAssignmentVerifier requires a non-empty key.")
        self._key = key

    def verify(self, payload: bytes, signature: str) -> bool:
        expected = hmac.new(self._key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


def sign_payload(payload: bytes, signing_key: bytes) -> str:
    return HMACAssignmentSigner(signing_key).sign(payload)


def _verify_fields_after_signature(
    assignment: RemoteExecutionAssignment,
    *,
    expected_tenant_id: str,
    expected_plan_id: str,
    expected_site_id: str,
    expected_seal_fingerprint: str,
    now: Optional[datetime],
) -> None:
    """Shared post-signature verification -- see verify_assignment's docstring for why
    signature must always be checked before any of these (attacker-controlled) fields."""
    if assignment.is_expired(now):
        raise StaleAssignmentError(f"Assignment {assignment.assignment_id!r} expired at {assignment.expires_at!r}.")

    if assignment.tenant_id != expected_tenant_id:
        raise WrongTenantError(f"Assignment {assignment.assignment_id!r} is for tenant {assignment.tenant_id!r}, expected {expected_tenant_id!r}.")

    if assignment.plan_id != expected_plan_id:
        raise WrongPlanError(f"Assignment {assignment.assignment_id!r} is for plan {assignment.plan_id!r}, expected {expected_plan_id!r}.")

    if assignment.site_id != expected_site_id:
        raise WrongSiteError(f"Assignment {assignment.assignment_id!r} is for site {assignment.site_id!r}, expected {expected_site_id!r}.")

    if assignment.execution_identity_seal_fingerprint != expected_seal_fingerprint:
        raise WrongSealError(
            f"Assignment {assignment.assignment_id!r} carries seal fingerprint "
            f"{assignment.execution_identity_seal_fingerprint!r}, expected {expected_seal_fingerprint!r}."
        )


def verify_assignment(
    assignment: RemoteExecutionAssignment,
    signing_key: bytes,
    *,
    expected_tenant_id: str,
    expected_plan_id: str,
    expected_site_id: str,
    expected_seal_fingerprint: str,
    now: Optional[datetime] = None,
) -> None:
    """
    Fail-closed verification of every dimension a compromised transport or a malicious
    remote site could try to tamper with, using the default symmetric HMAC scheme.
    Order matters: signature is checked FIRST so that a forged assignment is rejected
    before any of its (attacker-controlled) claimed fields are even trusted enough to
    compare. This function never performs (or replaces) an AKAAL authorization decision
    -- see the architecture note at the top of this module.
    """
    if not HMACAssignmentVerifier(signing_key).verify(assignment.canonical_payload(), assignment.signature):
        raise ForgedAssignmentError(f"Assignment {assignment.assignment_id!r} signature does not match its content; forged or tampered.")

    _verify_fields_after_signature(
        assignment,
        expected_tenant_id=expected_tenant_id,
        expected_plan_id=expected_plan_id,
        expected_site_id=expected_site_id,
        expected_seal_fingerprint=expected_seal_fingerprint,
        now=now,
    )


def verify_assignment_with_verifier(
    assignment: RemoteExecutionAssignment,
    verifier: AssignmentVerifier,
    *,
    expected_tenant_id: str,
    expected_plan_id: str,
    expected_site_id: str,
    expected_seal_fingerprint: str,
    now: Optional[datetime] = None,
) -> None:
    """KMS/asymmetric-signing-ready counterpart to verify_assignment -- identical
    semantics, but delegates the signature check to a caller-supplied AssignmentVerifier
    (e.g. wrapping a real KeyManagementProvider.verify) instead of requiring raw HMAC key
    bytes. `verifier.verify()` returning anything other than True is treated as forged."""
    if verifier.verify(assignment.canonical_payload(), assignment.signature) is not True:
        raise ForgedAssignmentError(f"Assignment {assignment.assignment_id!r} signature does not match its content; forged or tampered.")

    _verify_fields_after_signature(
        assignment,
        expected_tenant_id=expected_tenant_id,
        expected_plan_id=expected_plan_id,
        expected_site_id=expected_site_id,
        expected_seal_fingerprint=expected_seal_fingerprint,
        now=now,
    )
