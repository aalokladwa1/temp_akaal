"""
akaalEngine.fabric.ownership.manager
=======================================
P7B.25 -- Distributed Execution Ownership, Leasing & Fencing.

OwnershipManager is the single authority answering "who is currently the one valid owner
of this exclusive unit of Fabric work" for applicable distributed execution. It is
explicitly NOT a second migration lifecycle engine (P7B Group-3 §9/§32 discipline) -- it
tracks exactly one thing: which (site, worker) generation currently holds execution
authority for one (tenant, migration, plan) unit of work, bound to the full trusted
context that was true at acquisition time.

Composition, not duplication:
    * Site trust/tenant-binding/execution-readiness -- delegated entirely to the supplied
      akaalEngine.fabric.execution_site.SiteRegistry. This module contains NO independent
      site-trust logic.
    * Fencing-generation issuance -- delegated entirely to the supplied
      akaalEngine.durability.fencing.manager.FencingTokenManager (Durability Authority #5).
      Every new ownership generation for a given ownership_key is minted by calling
      `issue_token(resource_id=ownership_key, ...)`, so ownership fencing and Authority #5
      fencing are the SAME monotonic, durable, HMAC-signed ledger -- never a second,
      parallel fencing universe.
    * Persistence -- delegated to akaalEngine.fabric.durability.FabricDurabilityStore
      (extended with save_ownership_record/load_ownership_record/list_ownership_keys),
      the same canonical Authority #5-backed store already used for Site/Environment/
      Topology/Locality/Worker state. No second persistence authority is created.

Time semantics (P7B.25 Section 6, answered honestly rather than glossed over):
    Lease expiry is judged by wall-clock (UTC ISO-8601) comparison, matching the
    already-frozen precedent in akaalPipeline.operations.leases.ExecutionLease. This is a
    BOUNDED guarantee: it is correct as long as cooperating processes' clocks drift by
    meaningfully less than the configured ttl_seconds (ordinary NTP-disciplined clocks in
    one deployment easily satisfy this; this module does not claim, and does not need,
    a perfect global clock). Fencing-generation comparison (not time) is what actually
    prevents a stale owner from continuing physical effects -- expiry only ever WIDENS who
    is eligible to acquire the next generation, it never itself grants authority. A caller
    at a genuine physical-effect boundary (source read, target write, checkpoint advance)
    is expected to call `validate()` immediately before acting, and `validate()`'s fencing-
    generation check is what is actually load-bearing there.

ABA protection: `acquire()` mints a brand-new fencing generation (via FencingTokenManager,
which increments monotonically and durably regardless of caller) every time it grants a
FRESH ownership grant (no active record, or the active record has expired/been released).
A previously valid owner presenting an old lease_id/fencing_generation can never again
match the current record once a newer generation has been minted -- there is no code path
that treats "this generation number was valid once" as sufficient; only "this generation
number is the CURRENT one" is ever accepted.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, Optional

from akaalEngine.durability.fencing.manager import FencingTokenManager
from akaalEngine.fabric.execution_site.registry import SiteRegistry
from akaalEngine.fabric.ownership.models import (
    LeaseConflictError,
    LeaseExpiredError,
    OwnershipClaim,
    OwnershipError,
    OwnershipRecord,
    OwnershipState,
    SiteNotExecutionReadyError,
    StaleFencingGenerationError,
    UnknownOwnershipError,
    WrongAssignmentOwnershipError,
    WrongExecutionOwnershipError,
    WrongPlanOwnershipError,
    WrongSealOwnershipError,
    WrongSiteOwnershipError,
    WrongTenantOwnershipError,
    WrongWorkerOwnershipError,
    _now_iso,
    _add_seconds_iso,
)


class OwnershipManager:
    def __init__(
        self,
        site_registry: SiteRegistry,
        fencing_manager: FencingTokenManager,
        durability_store: Optional[Any] = None,
    ) -> None:
        self.site_registry = site_registry
        self.fencing_manager = fencing_manager
        self._durability_store = durability_store
        self._lock = threading.RLock()
        self._records: Dict[str, OwnershipRecord] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist(self, record: OwnershipRecord) -> None:
        if self._durability_store is not None:
            self._durability_store.save_ownership_record(record)

    def _register_reconstructed(self, record: OwnershipRecord) -> None:
        """INTERNAL ONLY -- rehydrates already-authoritative durable state after a
        fresh-process restart. Never call with caller-supplied/untrusted input."""
        with self._lock:
            self._records[record.ownership_key] = record

    def _require_site_execution_ready(self, site_id: str, tenant_id: str) -> None:
        site = self.site_registry.get(site_id)  # UnknownSiteError propagates -- fail safe
        if not site.is_execution_authorized() or site.tenant_binding != tenant_id:
            raise SiteNotExecutionReadyError(
                f"Site {site_id!r} is not currently execution-ready for tenant "
                f"{tenant_id!r} (trust_state must be TRUSTED, tenant_binding must match, "
                f"lifecycle_state must be ACTIVE); ownership cannot be acquired or "
                f"renewed against a site whose trust has lapsed."
            )

    @staticmethod
    def _check_context_matches(existing: OwnershipRecord, claim: OwnershipClaim) -> None:
        """
        Validates the dimensions that identify ONE logical execution binding and must
        never change across the lifetime of one ownership generation: tenant, plan
        (id+fingerprint), seal, and execution. `assignment_id` is deliberately NOT checked
        here -- see the module docstring's "Assignment binding" note and
        `assignment_consistent_with_ownership` below: a legitimate long-running physical
        transport dispatch (`execute_via_placement`) issues a FRESH, freshly-signed
        `RemoteExecutionAssignment` on every call for the SAME ownership generation (this
        is Group-1's own, unmodified assignment-issuance behavior), so treating
        assignment_id as a frozen, must-match-forever field would incorrectly fence a
        renewing owner's OWN legitimate re-dispatch. What genuinely must never happen --
        an assignment for a DIFFERENT site/tenant/plan being accepted under this
        ownership record -- is already caught by the tenant/plan/seal checks below (an
        assignment's own site_id/tenant_id/plan_id are themselves derived from the same
        immutable PlacementDecision an ownership claim is built from, never independently
        caller-supplied) and, structurally, by `assignment_consistent_with_ownership`.
        """
        if existing.tenant_id != claim.tenant_id:
            raise WrongTenantOwnershipError(
                f"Ownership {existing.ownership_key!r} belongs to tenant "
                f"{existing.tenant_id!r}, not {claim.tenant_id!r}."
            )
        if existing.plan_id != claim.plan_id or existing.plan_fingerprint != claim.plan_fingerprint:
            raise WrongPlanOwnershipError(
                f"Ownership {existing.ownership_key!r} is bound to plan_id="
                f"{existing.plan_id!r}/plan_fingerprint={existing.plan_fingerprint!r}, "
                f"not plan_id={claim.plan_id!r}/plan_fingerprint={claim.plan_fingerprint!r}."
            )
        if existing.execution_identity_seal_fingerprint != claim.execution_identity_seal_fingerprint:
            raise WrongSealOwnershipError(
                f"Ownership {existing.ownership_key!r} is bound to seal fingerprint "
                f"{existing.execution_identity_seal_fingerprint!r}, not "
                f"{claim.execution_identity_seal_fingerprint!r}."
            )
        if existing.execution_id != claim.execution_id:
            raise WrongExecutionOwnershipError(
                f"Ownership {existing.ownership_key!r} is bound to execution "
                f"{existing.execution_id!r}, not {claim.execution_id!r}."
            )

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------

    def acquire(self, claim: OwnershipClaim) -> OwnershipRecord:
        with self._lock:
            self._require_site_execution_ready(claim.site_id, claim.tenant_id)

            key = claim.ownership_key()
            existing = self._records.get(key)
            now = _now_iso()

            if existing is not None and existing.is_currently_valid_owner(now):
                if existing.worker_id != claim.worker_id or existing.site_id != claim.site_id:
                    raise LeaseConflictError(
                        f"Ownership key {key!r} is actively held by worker "
                        f"{existing.worker_id!r} at site {existing.site_id!r} until "
                        f"{existing.expires_at!r}; concurrent acquisition by worker "
                        f"{claim.worker_id!r} at site {claim.site_id!r} refused."
                    )
                # Same worker/site re-acquiring before expiry -- treat as a renewal
                # (idempotent re-entry), never as a fresh generation.
                self._check_context_matches(existing, claim)
                renewed = OwnershipRecord(
                    **{**existing.__dict__, "expires_at": _add_seconds_iso(now, claim.ttl_seconds), "assignment_id": claim.assignment_id}
                )
                self._records[key] = renewed
                self._persist(renewed)
                return renewed

            # No existing record, or the existing one has expired/been released/
            # transferred away -- safe to mint a brand-new fencing generation. This is the
            # ONLY place a new generation is minted for a given ownership_key.
            token = self.fencing_manager.issue_token(resource_id=key, worker_id=claim.worker_id)
            record = OwnershipRecord(
                ownership_key=key,
                tenant_id=claim.tenant_id,
                workspace_id=claim.workspace_id,
                project_id=claim.project_id,
                migration_id=claim.migration_id,
                plan_id=claim.plan_id,
                plan_fingerprint=claim.plan_fingerprint,
                execution_identity_seal_fingerprint=claim.execution_identity_seal_fingerprint,
                execution_id=claim.execution_id,
                placement_id=claim.placement_id,
                assignment_id=claim.assignment_id,
                site_id=claim.site_id,
                worker_id=claim.worker_id,
                correlation_id=claim.correlation_id,
                actor_id=claim.actor_id,
                lease_id=f"own-{uuid.uuid4().hex[:20]}",
                fencing_generation=token.fencing_epoch,
                acquired_at=now,
                expires_at=_add_seconds_iso(now, claim.ttl_seconds),
                state=OwnershipState.ACTIVE,
            )
            self._records[key] = record
            self._persist(record)
            return record

    # ------------------------------------------------------------------
    # Renewal
    # ------------------------------------------------------------------

    def renew(self, claim: OwnershipClaim, lease_id: str, fencing_generation: int) -> OwnershipRecord:
        with self._lock:
            key = claim.ownership_key()
            existing = self._records.get(key)
            if existing is None:
                raise UnknownOwnershipError(f"No ownership record for key {key!r}.")

            if existing.state != OwnershipState.ACTIVE:
                raise LeaseConflictError(
                    f"Ownership {key!r} is in state {existing.state.value!r}, not ACTIVE; "
                    f"cannot renew a released/transferred-away lease."
                )
            if existing.lease_id != lease_id:
                raise LeaseConflictError(
                    f"Renewal for {key!r} presented lease_id {lease_id!r}, which does not "
                    f"match the current lease_id {existing.lease_id!r}."
                )
            if existing.is_expired():
                raise LeaseExpiredError(
                    f"Ownership {key!r} lease {lease_id!r} expired at "
                    f"{existing.expires_at!r}; expired ownership grants no authority to renew."
                )
            if existing.fencing_generation != fencing_generation:
                raise StaleFencingGenerationError(
                    f"Renewal for {key!r} presented fencing_generation {fencing_generation}, "
                    f"current generation is {existing.fencing_generation}; refusing stale/"
                    f"ABA renewal attempt."
                )
            if existing.worker_id != claim.worker_id:
                raise WrongWorkerOwnershipError(
                    f"Ownership {key!r} is held by worker {existing.worker_id!r}, not "
                    f"{claim.worker_id!r}."
                )
            if existing.site_id != claim.site_id:
                raise WrongSiteOwnershipError(
                    f"Ownership {key!r} is bound to site {existing.site_id!r}, not "
                    f"{claim.site_id!r}."
                )
            self._check_context_matches(existing, claim)

            # Current site trust MUST be re-checked on every renewal -- a site revoked
            # after acquisition must not continue renewing indefinitely on old trust.
            self._require_site_execution_ready(existing.site_id, existing.tenant_id)

            renewed = OwnershipRecord(
                **{**existing.__dict__, "expires_at": _add_seconds_iso(_now_iso(), claim.ttl_seconds), "assignment_id": claim.assignment_id}
            )
            self._records[key] = renewed
            self._persist(renewed)
            return renewed

    # ------------------------------------------------------------------
    # Transfer -- controlled Owner A/fencing N -> Owner B/fencing N+1
    # ------------------------------------------------------------------

    def transfer(
        self,
        current_lease_id: str,
        current_fencing_generation: int,
        new_claim: OwnershipClaim,
    ) -> OwnershipRecord:
        with self._lock:
            key = new_claim.ownership_key()
            existing = self._records.get(key)
            if existing is None:
                raise UnknownOwnershipError(f"No ownership record for key {key!r}.")

            if existing.state != OwnershipState.ACTIVE:
                raise LeaseConflictError(f"Ownership {key!r} is not ACTIVE; cannot transfer.")
            if existing.lease_id != current_lease_id:
                raise LeaseConflictError(
                    f"Transfer for {key!r} presented lease_id {current_lease_id!r}, which "
                    f"does not match the current lease_id {existing.lease_id!r}."
                )
            if existing.fencing_generation != current_fencing_generation:
                raise StaleFencingGenerationError(
                    f"Transfer for {key!r} presented fencing_generation "
                    f"{current_fencing_generation}, current generation is "
                    f"{existing.fencing_generation}; refusing stale transfer request."
                )
            if existing.is_expired():
                raise LeaseExpiredError(
                    f"Ownership {key!r} lease {current_lease_id!r} already expired at "
                    f"{existing.expires_at!r}; use acquire() for a fresh grant instead of "
                    f"transferring an already-expired lease."
                )
            # Transfer is a controlled continuation of the SAME logical unit of work --
            # tenant/plan/seal/execution must match; only site/worker/owner may change.
            self._check_context_matches(existing, new_claim)

            self._require_site_execution_ready(new_claim.site_id, new_claim.tenant_id)

            token = self.fencing_manager.issue_token(resource_id=key, worker_id=new_claim.worker_id)
            transferred_record = OwnershipRecord(
                ownership_key=key,
                tenant_id=new_claim.tenant_id,
                workspace_id=new_claim.workspace_id,
                project_id=new_claim.project_id,
                migration_id=new_claim.migration_id,
                plan_id=new_claim.plan_id,
                plan_fingerprint=new_claim.plan_fingerprint,
                execution_identity_seal_fingerprint=new_claim.execution_identity_seal_fingerprint,
                execution_id=new_claim.execution_id,
                placement_id=new_claim.placement_id,
                assignment_id=new_claim.assignment_id,
                site_id=new_claim.site_id,
                worker_id=new_claim.worker_id,
                correlation_id=new_claim.correlation_id,
                actor_id=new_claim.actor_id,
                lease_id=f"own-{uuid.uuid4().hex[:20]}",
                fencing_generation=token.fencing_epoch,
                acquired_at=_now_iso(),
                expires_at=_add_seconds_iso(_now_iso(), new_claim.ttl_seconds),
                state=OwnershipState.ACTIVE,
            )
            # The old generation is marked TRANSFERRED (informational; the authoritative
            # staleness signal is that its fencing_generation no longer matches current).
            stale_old = OwnershipRecord(**{**existing.__dict__, "state": OwnershipState.TRANSFERRED})
            self._persist(stale_old)

            self._records[key] = transferred_record
            self._persist(transferred_record)
            return transferred_record

    # ------------------------------------------------------------------
    # Validation -- the load-bearing check at physical-effect boundaries
    # ------------------------------------------------------------------

    def validate(self, ownership_key: str, lease_id: str, fencing_generation: int) -> OwnershipRecord:
        """
        Raises on ANY violation; returns the current record only on full success. Callers
        at a genuine physical-effect boundary (source read, target write, checkpoint
        advance, CDC apply) MUST call this immediately before acting and must treat any
        exception as an absolute stop -- this is where fencing is actually load-bearing.
        """
        with self._lock:
            existing = self._records.get(ownership_key)
            if existing is None:
                raise UnknownOwnershipError(f"No ownership record for key {ownership_key!r}.")
            if existing.state != OwnershipState.ACTIVE:
                raise LeaseConflictError(
                    f"Ownership {ownership_key!r} is in state {existing.state.value!r}, "
                    f"not ACTIVE; stale owner rejected."
                )
            if existing.is_expired():
                raise LeaseExpiredError(
                    f"Ownership {ownership_key!r} lease expired at {existing.expires_at!r}."
                )
            if existing.lease_id != lease_id:
                raise LeaseConflictError(
                    f"Presented lease_id {lease_id!r} does not match current lease_id "
                    f"{existing.lease_id!r} for {ownership_key!r}."
                )
            if existing.fencing_generation != fencing_generation:
                raise StaleFencingGenerationError(
                    f"Presented fencing_generation {fencing_generation} does not match "
                    f"current generation {existing.fencing_generation} for "
                    f"{ownership_key!r}; stale owner rejected."
                )
            return existing

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def release(self, ownership_key: str, lease_id: str, fencing_generation: int) -> None:
        with self._lock:
            existing = self.validate(ownership_key, lease_id, fencing_generation)
            released = OwnershipRecord(**{**existing.__dict__, "state": OwnershipState.RELEASED})
            self._records[ownership_key] = released
            self._persist(released)

    def try_get(self, ownership_key: str) -> Optional[OwnershipRecord]:
        with self._lock:
            return self._records.get(ownership_key)

    # ------------------------------------------------------------------
    # Administrative force-fence -- for confirmed-dead/unresponsive owners only
    # ------------------------------------------------------------------

    def force_fence(self, ownership_key: str, *, reason: str, evidence: str) -> Optional[OwnershipRecord]:
        """
        Marks the current ACTIVE record (if any) FENCED, WITHOUT requiring the caller to
        present its lease_id/fencing_generation -- this is the one deliberate exception to
        "no mutating call succeeds without matching lease/generation", and it exists
        specifically for the P7B.28 disaster-recovery case: the old owner's site has
        genuinely failed and cannot cooperate in a graceful transfer() (which requires
        presenting the current lease/generation) or release().

        This is a fail-CLOSED protective action (identical justification to
        akaalEngine.fabric.execution_site.registry.SiteRegistry.revoke, which is likewise
        "always permitted without an authorization callback -- fail-closed actions never
        need extra permission; only fail-open (elevating) actions do") -- it can only ever
        remove authority, never grant it. `reason`/`evidence` are mandatory non-empty
        strings so every force-fence is traceable; callers (in production, the P7B.28
        failover orchestration, never a bare caller assertion) are expected to supply
        evidence sourced from an independent authority (e.g. a P7B.24 SiteCoordinator
        CoordinationView of UNAVAILABLE_STALE/PARTITIONED_UNCERTAIN/REVOKED for the
        record's site_id) -- this method itself does not verify that evidence; it trusts
        its caller exactly as much as SiteRegistry.revoke trusts ITS caller, no more.

        Returns None (a no-op) if there is no ACTIVE record for this key -- force-fencing
        an already-inactive or nonexistent record is not an error, since the desired end
        state (no active claimant) already holds.
        """
        if not reason or not reason.strip():
            raise OwnershipError("force_fence requires a non-empty reason for audit.")
        if not evidence or not evidence.strip():
            raise OwnershipError("force_fence requires non-empty evidence for audit.")
        with self._lock:
            existing = self._records.get(ownership_key)
            if existing is None or existing.state != OwnershipState.ACTIVE:
                return existing
            fenced = OwnershipRecord(**{**existing.__dict__, "state": OwnershipState.FENCED})
            self._records[ownership_key] = fenced
            self._persist(fenced)
            return fenced


def assignment_consistent_with_ownership(
    record: OwnershipRecord, *, assignment_site_id: str, assignment_tenant_id: str, assignment_plan_id: str,
) -> None:
    """
    Point-of-use consistency check for the "assignment substitution" hostile scenario:
    proves that a specific `RemoteExecutionAssignment` about to be used for physical work
    genuinely belongs to the SAME (tenant, plan, site) unit of work the CURRENT ownership
    record is authoritative for -- e.g. a caller (or a confused-deputy code path) trying
    to use a validly-held ownership record to authorize physical effects for an
    ENTIRELY DIFFERENT assignment (different site/tenant/plan) is rejected here.

    This is deliberately NOT the same thing as `OwnershipManager.renew()`'s own context
    checks (which bind the OWNERSHIP RECORD's identity across its lifetime) -- this
    function binds a SPECIFIC, freshly-issued assignment to whatever the CURRENT record
    says, at the moment that assignment is about to be used, which is what actually closes
    the substitution attack for a system where a fresh assignment is legitimately reissued
    on every physical dispatch.

    Raises the same `WrongSiteOwnershipError`/`WrongTenantOwnershipError`/
    `WrongAssignmentOwnershipError` family `renew`/`transfer` already use, rather than a
    parallel exception hierarchy.
    """
    if record.site_id != assignment_site_id:
        raise WrongSiteOwnershipError(
            f"Assignment targets site {assignment_site_id!r}, but ownership {record.ownership_key!r} "
            f"is bound to site {record.site_id!r}; refusing to use this assignment under this ownership."
        )
    if record.tenant_id != assignment_tenant_id:
        raise WrongTenantOwnershipError(
            f"Assignment belongs to tenant {assignment_tenant_id!r}, but ownership "
            f"{record.ownership_key!r} is bound to tenant {record.tenant_id!r}."
        )
    if record.plan_id != assignment_plan_id:
        raise WrongAssignmentOwnershipError(
            f"Assignment belongs to plan {assignment_plan_id!r}, but ownership "
            f"{record.ownership_key!r} is bound to plan {record.plan_id!r}; refusing "
            f"assignment substitution."
        )
