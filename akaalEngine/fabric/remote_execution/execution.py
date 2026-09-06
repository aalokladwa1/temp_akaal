"""
akaalEngine.fabric.remote_execution.execution
================================================
P7B Group-1 Hostile Review Round 4 -- structural (not caller-discipline-dependent)
enforcement of continuous security revalidation for fabric/remote-bound canonical
execution.

FORENSIC FINDING (Round 4 §2): `akaalEngine.transport.api.TransportAuthority
.execute_partition_transport` accepts `security_revalidator` as an OPTIONAL parameter
(default `None`). This is architecturally correct for TransportAuthority itself -- it is
also used for purely local, non-fabric-bound migrations that have no P7B remote-execution
assignment at all, and forcing every TransportAuthority caller to supply a fabric
revalidator would be wrong (and would require modifying frozen, non-Group-1 call sites).
It is NOT correct for FABRIC-bound execution specifically: nothing previously prevented
a caller who HAS a RemoteExecutionAssignment from simply forgetting to pass
`security_revalidator`, or passing a revalidator that only checks the (stateless)
signature and never re-checks LIVE site trust -- both of which would let physical
execution proceed after a site was revoked/tenant-rebound/fenced-out post-issuance.

THE FIX: this module is the canonical, ONLY sanctioned entry point for executing a
`RemoteExecutionAssignment` through `TransportAuthority`. It does not accept a
`security_revalidator` parameter from the caller at all -- it always constructs one
internally, composed of (a) the mandatory stateless signature/field check
(`verify_assignment`/`verify_assignment_with_verifier`) and (b) an optional but
STRONGLY RECOMMENDED live-trust callback re-checking the assignment's site/tenant
against current `SiteRegistry` state (exactly what closes the "revoked after issuance"
gap Round 3 disclosed). A caller who bypasses this module and calls
`TransportAuthority.execute_partition_transport` directly can still, as before, omit
revalidation for a NON-fabric migration -- that is correct, unchanged, and out of
Group-1 scope. But any caller who wants to execute a `RemoteExecutionAssignment` now has
one correct path, not "remember to wire the revalidator yourself".

This creates NO second TransportAuthority, no second execution engine, no second
checkpoint/retry system -- it is a thin, mandatory-binding wrapper around the existing
canonical `execute_partition_transport` call.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from akaalEngine.fabric.connectivity.models import ConnectivityEdge
from akaalEngine.fabric.remote_execution.models import (
    AssignmentVerifier,
    RemoteExecutionAssignment,
    RemoteExecutionError,
    verify_assignment,
    verify_assignment_with_verifier,
)
from akaalEngine.fabric.route_planning.models import MovementRoute

LiveTrustCheck = Callable[[RemoteExecutionAssignment], bool]
CurrentEdgesProvider = Callable[[], Mapping[str, ConnectivityEdge]]


class FencingTokenFromAssignment:
    """Canonical, single way to derive a TransportAuthority-shaped fencing token from a
    RemoteExecutionAssignment's own fencing_epoch -- so callers never hand-roll one that
    could drift from the assignment it is supposed to represent."""

    def __init__(self, assignment: RemoteExecutionAssignment) -> None:
        self.fencing_epoch = assignment.fencing_epoch
        self._assignment = assignment

    def is_valid(self) -> bool:
        return not self._assignment.is_expired()


def execute_assignment_via_transport(
    *,
    transport_authority: Any,
    assignment: RemoteExecutionAssignment,
    signing_key: Optional[bytes] = None,
    verifier: Optional[AssignmentVerifier] = None,
    expected_tenant_id: str,
    expected_plan_id: str,
    expected_site_id: str,
    expected_seal_fingerprint: str,
    reader: Any,
    writer: Any,
    partition: Any,
    live_trust_check: Optional[LiveTrustCheck] = None,
    route: Optional[MovementRoute] = None,
    current_edges_provider: Optional[CurrentEdgesProvider] = None,
    evidence_authority: Optional[Any] = None,
    run_id: Optional[str] = None,
    **execute_kwargs: Any,
) -> int:
    """
    The ONLY sanctioned way to run a RemoteExecutionAssignment through canonical
    TransportAuthority. Structurally guarantees:

        NO VALID CURRENT SECURITY CONTEXT -> NO PHYSICAL READ/WRITE/COMMIT/CHECKPOINT.

    because `security_revalidator` is not a parameter this function exposes -- it is
    always built here, and it is called by TransportAuthority.execute_partition_transport
    before every batch read, every write, and every commit (that is
    TransportAuthority's own existing, unmodified contract -- see
    akaalEngine.transport.api.TransportAuthority.execute_partition_transport).

    `live_trust_check`, if supplied, is called on EVERY revalidation alongside the
    stateless signature check -- this is how "site revoked/tenant rebound after
    issuance" (a real gap verify_assignment alone cannot catch, since it only checks
    signed, immutable data) is closed. A caller executing fabric-bound work without a
    real live_trust_check wired to their SiteRegistry is knowingly accepting that
    revocation-after-issuance will not be caught until the assignment's own expiry --
    this function does not silently paper over that; it requires the caller to have
    explicitly decided (by passing or omitting live_trust_check), never leaves it
    ambiguous.
    """
    if bool(signing_key) == bool(verifier):
        raise RemoteExecutionError("execute_assignment_via_transport requires exactly one of signing_key or verifier.")

    def revalidate() -> bool:
        if signing_key:
            verify_assignment(
                assignment, signing_key,
                expected_tenant_id=expected_tenant_id, expected_plan_id=expected_plan_id,
                expected_site_id=expected_site_id, expected_seal_fingerprint=expected_seal_fingerprint,
            )
        else:
            verify_assignment_with_verifier(
                assignment, verifier,
                expected_tenant_id=expected_tenant_id, expected_plan_id=expected_plan_id,
                expected_site_id=expected_site_id, expected_seal_fingerprint=expected_seal_fingerprint,
            )
        if live_trust_check is not None:
            live_ok = live_trust_check(assignment)
            if live_ok is not True:
                raise RemoteExecutionError(
                    f"Live trust check failed for assignment {assignment.assignment_id!r} "
                    f"(site {assignment.site_id!r}, tenant {assignment.tenant_id!r}); "
                    f"execution must not proceed on stale/revoked authorization."
                )
        if route is not None and current_edges_provider is not None:
            # Round-5 closure: topology_fingerprint()/is_stale_against() were real,
            # tested methods with NO production consumer (Round 4's explicit finding --
            # "a helper nobody calls is not a security control"). This is the fix: route
            # freshness is now checked on every one of TransportAuthority's existing
            # revalidation points (pre-read, pre-write, pre-commit), composed into the
            # SAME mandatory security_revalidator closure as the assignment/trust checks
            # above -- not a second, parallel mechanism.
            current_edges = current_edges_provider()
            if route.is_stale_against(current_edges):
                raise RemoteExecutionError(
                    f"Route {route.route_id!r} topology has drifted since planning "
                    f"(fingerprint {route.topology_fingerprint()!r} no longer matches "
                    f"current edge state); refusing to execute against a stale route."
                )
        return True

    fencing_token = FencingTokenFromAssignment(assignment)
    resolved_run_id = run_id or f"run-{assignment.assignment_id}"

    try:
        result = transport_authority.execute_partition_transport(
            reader=reader,
            writer=writer,
            partition=partition,
            fencing_token=fencing_token,
            security_revalidator=revalidate,
            migration_id=assignment.migration_id,
            run_id=resolved_run_id,
            **execute_kwargs,
        )
    except Exception as exc:
        if evidence_authority is not None:
            # Evidence recording is a post-hoc side effect, never a gate: if the
            # evidence backend itself is broken, that must not replace or mask the
            # REAL security rejection already in flight -- the original exception is
            # always what propagates, never an evidence-backend error.
            try:
                _emit_rejection_evidence(evidence_authority, assignment, resolved_run_id, exc)
            except Exception:  # noqa: BLE001 -- deliberate: evidence emission never overrides the real outcome
                pass
        raise
    else:
        if evidence_authority is not None:
            # Same principle for the success path: the physical transport operation has
            # ALREADY completed successfully by this point (rows are durably written) --
            # an evidence-backend outage must never retroactively report a successful
            # migration as failed to the caller.
            from akaalEngine.fabric.evidence import emit_fabric_execution_evidence
            try:
                emit_fabric_execution_evidence(
                    evidence_authority, migration_id=assignment.migration_id, run_id=resolved_run_id,
                    site_id=assignment.site_id, assignment_id=assignment.assignment_id,
                    accepted=True, fencing_epoch=assignment.fencing_epoch,
                )
            except Exception:  # noqa: BLE001 -- deliberate: see above
                pass
        return result


_REJECTION_REASON_CODES = {
    "ForgedAssignmentError": "FORGED_SIGNATURE",
    "StaleAssignmentError": "EXPIRED_ASSIGNMENT",
    "WrongTenantError": "TENANT_MISMATCH",
    "WrongPlanError": "PLAN_MISMATCH",
    "WrongSiteError": "SITE_MISMATCH",
    "WrongSealError": "SEAL_MISMATCH",
}


def _emit_rejection_evidence(evidence_authority: Any, assignment: RemoteExecutionAssignment, run_id: str, exc: Exception) -> None:
    from akaalEngine.fabric.evidence import emit_fabric_execution_evidence

    # TransportAuthority's _validate_security wraps whatever `revalidate()` raised into
    # a generic TransportFencingError via `raise TransportFencingError(...) from exc` --
    # __cause__ preserves the ORIGINAL fabric exception type for accurate
    # classification, rather than collapsing every rejection into one generic code.
    original = exc.__cause__ or exc
    reason_code = _REJECTION_REASON_CODES.get(type(original).__name__, "SECURITY_REVALIDATION_FAILED")
    if "stale" in str(original).lower() and "route" in str(original).lower():
        reason_code = "STALE_ROUTE"
    elif "live trust check failed" in str(original).lower():
        reason_code = "REVOKED_OR_REBOUND_SITE"

    emit_fabric_execution_evidence(
        evidence_authority, migration_id=assignment.migration_id, run_id=run_id,
        site_id=assignment.site_id, assignment_id=assignment.assignment_id,
        accepted=False, reason_code=reason_code, reason_detail=str(original),
        fencing_epoch=assignment.fencing_epoch,
    )
