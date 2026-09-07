"""
akaalEngine.fabric.ownership.models
======================================
P7B.25 -- Distributed Execution Ownership, Leasing & Fencing data model.

An OwnershipRecord is the single source of truth for "which worker, at which site, is
currently authorized to perform physical effects for one exclusive unit of AKAAL Fabric
work" -- bound to the full trusted context (tenant/workspace/project/migration/plan/
plan_fingerprint/seal/execution/placement/assignment/site/worker/correlation), never to
a bare identifier alone (P7B Group-3 permanent laws: "Site ID != authorization",
"Worker ID != authorization", "Lease ID != authorization").

This module does NOT duplicate:
    * akaalEngine.fabric.execution_site.SiteRegistry (site trust/tenant-binding ladder --
      OwnershipManager delegates every site-trust question to it, never re-implements);
    * akaalEngine.durability.fencing.manager.FencingTokenManager (the durable, HMAC-signed,
      monotonic per-resource fencing-epoch ledger -- OwnershipManager mints every fencing
      generation through it, so ownership fencing and Durability Authority #5 fencing are
      the SAME ledger for a given ownership resource, never a second fencing universe).

Expiry uses wall-clock (UTC ISO-8601) comparison, deliberately mirroring the
already-frozen precedent in akaalPipeline.operations.leases.ExecutionLease (P5/P6-era
canonical execution-attempt leasing) rather than inventing a new time model: this is an
honest, bounded guarantee (correct as long as TTLs are set comfortably larger than
plausible clock drift between cooperating processes), not a claim of a perfect
distributed clock -- see OwnershipManager's module docstring for the full discussion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class OwnershipError(RuntimeError):
    pass


class UnknownOwnershipError(KeyError):
    """No OwnershipRecord exists for the given ownership_key -- fails safe, never
    fabricates a default record."""


class LeaseConflictError(OwnershipError):
    """Raised when: (a) acquisition is attempted while a different worker actively,
    unexpired-ly holds the same ownership_key; (b) a renew/transfer/release/validate call
    presents a lease_id that does not match the currently recorded lease."""


class StaleFencingGenerationError(OwnershipError):
    """Raised when a caller presents a fencing_generation that does not match the
    currently recorded generation for this ownership_key -- covers both plain staleness
    and ABA (an old, once-valid generation reappearing after a newer one has already been
    issued)."""


class LeaseExpiredError(OwnershipError):
    """Raised when an operation requires an unexpired lease and the current record's
    wall-clock expiry has already passed. Expired ownership grants no further authority."""


class SiteNotExecutionReadyError(OwnershipError):
    """Raised when the claimed site_id is not currently TRUSTED + tenant-bound + ACTIVE
    per SiteRegistry (checked both at initial acquisition AND at every renewal -- a site
    revoked after acquisition must cause renewal to fail closed, not silently continue)."""


class OwnershipContextMismatchError(OwnershipError):
    """Base class for every trusted-context binding violation below. Each dimension gets
    its own concrete subclass so hostile tests (and callers) can distinguish exactly
    which binding failed, mirroring
    akaalEngine.fabric.remote_execution.models's WrongTenantError/WrongPlanError/
    WrongSealError/WrongSiteError pattern."""


class WrongTenantOwnershipError(OwnershipContextMismatchError):
    pass


class WrongPlanOwnershipError(OwnershipContextMismatchError):
    pass


class WrongSealOwnershipError(OwnershipContextMismatchError):
    pass


class WrongAssignmentOwnershipError(OwnershipContextMismatchError):
    pass


class WrongSiteOwnershipError(OwnershipContextMismatchError):
    pass


class WrongWorkerOwnershipError(OwnershipContextMismatchError):
    pass


class WrongExecutionOwnershipError(OwnershipContextMismatchError):
    pass


class OwnershipState(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    TRANSFERRED = "TRANSFERRED"
    FENCED = "FENCED"


def _now_iso() -> str:
    """
    NOTE (found during P7B.25 hostile self-review): on some platforms/CPython builds,
    back-to-back calls to `datetime.now(timezone.utc)` within the same clock tick can
    return an IDENTICAL value (observed on this project's Windows dev environment: 20
    rapid successive calls all returned the same microsecond-precision timestamp). This
    means two renewals issued in immediate succession can legitimately produce the SAME
    `expires_at` string rather than a strictly later one. This is NOT a security defect --
    ttl_seconds (default 30s) is many orders of magnitude larger than any observed clock
    quantization, so "is this lease still within its TTL window" remains correct -- but it
    means callers (including this module's own tests) must never assert strict
    `new_expires_at > old_expires_at` without first ensuring real wall-clock time has
    elapsed (e.g. via a short sleep); asserting `>=` or checking absolute TTL distance is
    the safe pattern.
    """
    return datetime.now(timezone.utc).isoformat()


def _add_seconds_iso(base_iso: str, seconds: float) -> str:
    base = datetime.fromisoformat(base_iso)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return (base + timedelta(seconds=seconds)).isoformat()


def _is_past(deadline_iso: str, now_iso: Optional[str] = None) -> bool:
    now = now_iso or _now_iso()
    return now >= deadline_iso


@dataclass(frozen=True)
class OwnershipClaim:
    """
    A request to acquire, renew, or transfer ownership. Every field here is the CALLER's
    already-verified trusted context (in production: read from the canonical
    ExecutionPlan/ExecutionIdentitySeal/PlacementDecision/RemoteExecutionAssignment
    objects upstream -- this module never re-derives or re-verifies plan/seal content
    itself, only compares it byte-for-byte against what a prior OwnershipRecord already
    recorded).
    """

    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_fingerprint: str
    execution_identity_seal_fingerprint: str
    execution_id: str
    placement_id: str
    assignment_id: str
    site_id: str
    worker_id: str
    correlation_id: str
    actor_id: Optional[str] = None  # informational/correlation only -- never compared for authorization
    ttl_seconds: float = 30.0

    def __post_init__(self) -> None:
        required = (
            "tenant_id", "workspace_id", "project_id", "migration_id", "plan_id",
            "plan_fingerprint", "execution_identity_seal_fingerprint", "execution_id",
            "placement_id", "assignment_id", "site_id", "worker_id", "correlation_id",
        )
        for name in required:
            if not getattr(self, name):
                raise OwnershipError(f"OwnershipClaim.{name} must be non-empty.")
        if self.ttl_seconds <= 0:
            raise OwnershipError("OwnershipClaim.ttl_seconds must be > 0.")

    def ownership_key(self) -> str:
        """The exclusive unit of work this claim contends for. Deliberately narrower than
        the full context (tenant+migration+plan only) -- execution_id/placement_id/
        assignment_id are expected to change across re-placement/failover for the SAME
        logical migration+plan, and it is exactly that logical unit which must have only
        one valid owner at a time."""
        return f"{self.tenant_id}::{self.migration_id}::{self.plan_id}"


@dataclass(frozen=True)
class OwnershipRecord:
    """Immutable snapshot of one ownership generation. Construct only via
    OwnershipManager -- never by hand, which is exactly the "forged lease" hostile case
    OwnershipManager.validate/renew/transfer exist to catch (there is no signature on this
    record itself; its integrity is enforced by requiring every mutating call to be routed
    through OwnershipManager, which is the sole holder of the in-memory/durable
    source-of-truth map -- see OwnershipManager's module docstring)."""

    ownership_key: str
    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_fingerprint: str
    execution_identity_seal_fingerprint: str
    execution_id: str
    placement_id: str
    assignment_id: str
    site_id: str
    worker_id: str
    correlation_id: str
    actor_id: Optional[str]
    lease_id: str
    fencing_generation: int
    acquired_at: str
    expires_at: str
    state: OwnershipState = OwnershipState.ACTIVE

    def is_expired(self, now_iso: Optional[str] = None) -> bool:
        return _is_past(self.expires_at, now_iso)

    def is_currently_valid_owner(self, now_iso: Optional[str] = None) -> bool:
        return self.state == OwnershipState.ACTIVE and not self.is_expired(now_iso)
