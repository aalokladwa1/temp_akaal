"""
akaalEngine.fabric.placement.execution
==========================================
P7B Group-2 production integration -- the ONLY sanctioned way to turn a
`akaalEngine.fabric.placement.binding.PlacementDecision` into live physical execution.

STRUCTURAL NO-BYPASS LAW: `execute_via_placement` has NO `site_id` parameter. The only
site this function can ever execute against is `placement_decision.selected_site_id` --
read-only, embedded in an object this module did not construct (only
`placement.binding.decide_placement` constructs one, and only after capability/
authorization/residency filtering already accepted that site). There is no keyword
argument anywhere on this function's signature that lets a caller redirect execution to a
different site than the one Campaign C selected (verified by signature introspection in
tests, exactly like `k8s_runtime.pod_spec.build_worker_pod_spec`'s missing hostNetwork
parameter).

REUSE, NEVER DUPLICATE: this module creates no second TransportAuthority, no second
security-revalidation mechanism, no second fencing scheme. It delegates 100% of physical
execution to the existing, unmodified
`akaalEngine.fabric.remote_execution.execution.execute_assignment_via_transport` (Group-1,
frozen) and 100% of assignment issuance to the existing, unmodified
`akaalEngine.fabric.remote_execution.control_plane.RemoteExecutionControlPlane` (Group-1,
frozen). Its only original contribution is composing a RICHER `live_trust_check` closure
that additionally re-verifies placement-decision freshness, worker binding integrity, and
(optionally) a live residency recheck -- layered into the SAME mandatory revalidation
point `execute_assignment_via_transport` already calls before every physical read, write,
and commit. No new revalidation mechanism is introduced; the existing one is composed
with more checks.

KUBERNETES SUBSTRATE BOUNDARY: for a `SiteKind.KUBERNETES` site, `bind_worker_for_placement`
additionally requires (via a caller-supplied `pod_spec_factory`) that a valid, secure pod
spec can actually be constructed for the selected worker before binding proceeds -- this
is the "go through the production Kubernetes worker boundary" requirement made concrete:
the K8s path is not silently skippable, but this module still never talks to a live
Kubernetes API (none is available in this environment -- see progress.md P7B Group-2
§36) and never invents a second runtime; once bound, execution proceeds through the exact
same `execute_assignment_via_transport` call as every other substrate, because the
canonical AKAAL runtime underneath is substrate-independent by design.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping, Optional

from akaalEngine.fabric.connectivity.models import ConnectivityEdge
from akaalEngine.fabric.execution_site.models import ExecutionSite, SiteKind
from akaalEngine.fabric.ownership.manager import OwnershipManager, assignment_consistent_with_ownership
from akaalEngine.fabric.ownership.models import OwnershipClaim, OwnershipError
from akaalEngine.fabric.placement.binding import PlacementDecision, StalePlacementError
from akaalEngine.fabric.remote_execution.control_plane import RemoteExecutionControlPlane
from akaalEngine.fabric.remote_execution.execution import LiveTrustCheck, execute_assignment_via_transport
from akaalEngine.fabric.remote_execution.models import AssignmentVerifier, RemoteExecutionAssignment, RemoteExecutionError
from akaalEngine.fabric.route_planning.models import MovementRoute
from akaalEngine.fabric.execution_site.registry import SiteAuthorizationCallback
from akaalEngine.fabric.topology.graph import TopologyGraph
from akaalEngine.fabric.worker_fabric.models import WorkerNode, WorkerState
from akaalEngine.fabric.worker_fabric.registry import WorkerRegistry


class PlacementExecutionError(RuntimeError):
    pass


class WorkerNotAvailableError(PlacementExecutionError):
    """Raised when no schedulable worker exists for the placement-selected site. This is
    a deliberate hard stop -- this module never falls back to a different site (that
    would bypass Campaign C's decision) and never creates a worker out of thin air
    (worker registration/scale-out remains P7B.22's job, invoked separately, upstream)."""


class PlacementBindingIntegrityError(PlacementExecutionError):
    """Raised when the assignment issued does not match the PlacementDecision it was
    supposed to be bound to (site_id/correlation_id mismatch) -- closes the "assignment
    substitution" hostile scenario structurally, not by caller discipline."""


class KubernetesPodSpecRequiredError(PlacementExecutionError):
    """Raised when the selected site is SiteKind.KUBERNETES but no pod_spec_factory was
    supplied -- the Kubernetes worker boundary can never be silently skipped for a
    Kubernetes-kind site."""


def bind_worker_for_placement(
    decision: PlacementDecision,
    worker_registry: WorkerRegistry,
    site: ExecutionSite,
    *,
    pod_spec_factory: Optional[Callable[[WorkerNode], Mapping[str, Any]]] = None,
) -> WorkerNode:
    """
    Selects and reserves (transitions IDLE -> BUSY) exactly one schedulable WorkerNode
    already registered at `site.site_id` for `decision.tenant_id`. Deterministic
    selection (lowest fencing_epoch, then worker_id) -- never arbitrary/dict-order, same
    discipline as `k8s_runtime.crd.reconcile_worker_pool`'s scale-in selection.

    For a KUBERNETES-kind site, `pod_spec_factory` is REQUIRED (raises
    `KubernetesPodSpecRequiredError` if omitted) and is called with the selected worker;
    its return value must be a Mapping with `kind: "Pod"` (the shape
    `akaalEngine.fabric.k8s_runtime.pod_spec.build_worker_pod_spec` produces) or this
    function raises -- proving the K8s worker boundary was genuinely exercised, not
    bypassed, for a K8s-kind site.
    """
    if site.site_kind == SiteKind.KUBERNETES and pod_spec_factory is None:
        raise KubernetesPodSpecRequiredError(
            f"Site {site.site_id!r} is SiteKind.KUBERNETES but no pod_spec_factory was "
            f"supplied; the Kubernetes worker boundary cannot be silently skipped."
        )

    candidates = [
        w for w in worker_registry.list_workers_for_site(site.site_id, decision.tenant_id)
        if w.is_schedulable()
    ]
    if not candidates:
        raise WorkerNotAvailableError(
            f"No schedulable worker available for site {site.site_id!r} tenant "
            f"{decision.tenant_id!r}; refusing to fabricate one or fall back to a "
            f"different site."
        )
    selected = sorted(candidates, key=lambda w: (w.fencing_epoch, w.worker_id))[0]

    if pod_spec_factory is not None:
        pod_spec = pod_spec_factory(selected)
        if not isinstance(pod_spec, Mapping) or pod_spec.get("kind") != "Pod":
            raise KubernetesPodSpecRequiredError(
                f"pod_spec_factory for worker {selected.worker_id!r} did not return a "
                f"valid Pod spec mapping (kind='Pod'); refusing to bind."
            )

    bound = worker_registry.heartbeat(selected.worker_id, decision.tenant_id, state=WorkerState.BUSY)
    return bound


def worker_still_valid(worker_registry: WorkerRegistry, worker: WorkerNode) -> bool:
    """A worker is still a valid execution binding if it exists, belongs to the same
    tenant/site, is NOT in a terminal-for-this-purpose state (REVOKED/UNHEALTHY/STALE --
    DRAINING is deliberately still valid: draining means 'no NEW assignments', never
    'kill active work', per P7B.22's law), and its fencing_epoch is UNCHANGED from what
    was bound (a changed epoch means the worker was replaced underneath this execution --
    P7B.23's rolling-replacement/self-healing law: the replacement is a DIFFERENT worker
    identity even if it reused the same worker_id via a rolling upgrade in-place restart
    that this module cannot distinguish from a hijack, so it fails closed either way)."""
    try:
        current = worker_registry.get(worker.worker_id, worker.tenant_id)
    except Exception:
        return False
    if current.state in (WorkerState.REVOKED, WorkerState.UNHEALTHY, WorkerState.STALE):
        return False
    if current.fencing_epoch != worker.fencing_epoch:
        return False
    return True


def finalize_worker_after_dispatch(worker_registry: WorkerRegistry, worker: WorkerNode, tenant_id: str) -> None:
    """
    THE single, canonical post-dispatch worker lifecycle finalization point (P7B.35
    hostile-review finding: `execute_via_placement`'s own `finally` block performed this
    inline for the `data_transport` capability only; every OTHER physical-effect
    capability dispatched through `FabricPlacementExecutionPort`'s delegate branch --
    `cdc_capture`, `cdc_apply`, `incremental_apply`, etc. -- left its bound worker BUSY
    forever, since nothing ever called this for them). Called exactly once per bound
    worker per dispatch attempt, from BOTH `execute_via_placement` (refactored to call
    this instead of duplicating the logic) and `FabricPlacementExecutionPort`'s delegate
    branch, regardless of outcome (success, failure, exception, ownership/fencing
    rejection) -- this is why every call site wraps it in a `finally`.

    NEVER RESURRECTS A WORKER: reads the worker's CURRENT live state first, and only
    transitions BUSY -> IDLE. Any other current state (REVOKED, DRAINING, UNHEALTHY,
    STALE) is left completely untouched -- a worker revoked or put into draining WHILE
    its dispatch was in flight must never be silently reset to IDLE merely because that
    one dispatch finished (P7B.22/23 laws: revoked-cannot-heartbeat-back-to-life,
    draining-means-no-new-work-not-kill-current-work). This also makes the finalization
    naturally idempotent/double-release-safe: calling it twice for the same worker is a
    no-op the second time, because by then the worker is already IDLE (not BUSY), so nothing
    beyond the first call does anything -- there is no separate "already released" flag to
    maintain, and no second worker-lifecycle authority is created by this function.
    """
    try:
        current = worker_registry.get(worker.worker_id, tenant_id)
    except Exception:
        return  # worker no longer exists / cross-tenant -- nothing to finalize
    if current.state != WorkerState.BUSY:
        return  # REVOKED/DRAINING/UNHEALTHY/STALE/already-IDLE -- never overwritten
    try:
        worker_registry.heartbeat(worker.worker_id, tenant_id, state=WorkerState.IDLE)
    except Exception:  # noqa: BLE001 -- a race lost to a concurrent revoke/drain is not this call's problem
        pass


def acquire_ownership_for_physical_capability(
    ownership_manager: OwnershipManager,
    decision: PlacementDecision,
    worker: WorkerNode,
    *,
    capability: str,
    execution_id: Optional[str] = None,
    ttl_seconds: float = 300.0,
) -> Any:
    """
    Acquires/renews P7B.25 distributed ownership for ANY physical-effect capability
    dispatched against a Group-2 `PlacementDecision` -- not only the `data_transport`
    (bulk-transport-shaped) path `execute_via_placement` itself gates internally.

    WHY THIS EXISTS (found during P7B.35 hostile review): `akaalPipeline.adapters.
    fabric_engine_gateway.FabricPlacementExecutionPort` only overrides binding resolution
    for the `data_transport` capability -- every OTHER capability a fabric-required plan
    dispatches (`cdc_capture`, `cdc_apply`, `incremental_extract`, `incremental_apply`,
    `state_reconcile`, etc.) is delegated, unchanged, to whatever real capability-specific
    ExecutionPort the CapabilityResolver/BindingRegistry independently resolved -- a port
    that has never heard of Group-2 placement or Group-3 ownership. Group-2's own Step A.2
    placement-freshness gate (`akaalPipeline.execution.coordinator.advance_plan_execution`)
    already applies to every non-READ_ONLY node in a fabric-required plan regardless of
    capability -- this function is called from that SAME universal gate to close the
    ownership half of that same gap, without forcing CDC/incremental capabilities through
    `execute_via_placement`'s reader/writer/partition contract (architecturally wrong for
    stream-shaped CDC semantics, per this module's own docstring).

    There is no Group-1 `RemoteExecutionAssignment` for these capabilities (an Assignment
    is a data_transport-specific concept minted by `RemoteExecutionControlPlane`) -- this
    function never calls `control_plane.issue_assignment` a second time for the same
    execution (which would legitimately fail `SiteRegistry`'s per-site fencing-epoch
    replay check, since `decision.fencing_epoch` is fixed once per execution). The
    ownership_key (tenant::migration::plan) is identical across every capability of one
    execution, so a SINGLE ownership generation -- acquired once, renewed thereafter --
    covers every physical capability dispatched for it, matching the granularity Group-3
    ownership is meant to protect at (see P7B.25 module docstring).
    """
    claim = OwnershipClaim(
        tenant_id=decision.tenant_id, workspace_id=decision.workspace_id, project_id=decision.project_id,
        migration_id=decision.migration_id, plan_id=decision.plan_id,
        plan_fingerprint=decision.execution_identity_seal_fingerprint,
        execution_identity_seal_fingerprint=decision.execution_identity_seal_fingerprint,
        execution_id=execution_id or decision.decision_id,
        placement_id=decision.decision_id,
        assignment_id=f"capability:{capability}",
        site_id=decision.selected_site_id, worker_id=worker.worker_id,
        correlation_id=decision.correlation_id, ttl_seconds=ttl_seconds,
    )
    return ownership_manager.acquire(claim)


def execute_via_placement(
    *,
    decision: PlacementDecision,
    site: ExecutionSite,
    worker: WorkerNode,
    control_plane: RemoteExecutionControlPlane,
    worker_registry: WorkerRegistry,
    transport_authority: Any,
    signing_key: Optional[bytes] = None,
    signer: Optional[Any] = None,
    verifier: Optional[AssignmentVerifier] = None,
    site_authorization_callback: Optional[SiteAuthorizationCallback],
    reader: Any,
    writer: Any,
    partition: Any,
    current_topology_provider: Callable[[], TopologyGraph],
    residency_recheck: Optional[Callable[[], bool]] = None,
    extra_live_trust_check: Optional[LiveTrustCheck] = None,
    route: Optional[MovementRoute] = None,
    current_edges_provider: Optional[Callable[[], Mapping[str, ConnectivityEdge]]] = None,
    evidence_authority: Optional[Any] = None,
    run_id: Optional[str] = None,
    assignment_ttl_minutes: float = 15.0,
    ownership_manager: Optional[OwnershipManager] = None,
    execution_id: Optional[str] = None,
    ownership_ttl_seconds: float = 300.0,
    telemetry_authority: Optional[Any] = None,
    **execute_kwargs: Any,
) -> int:
    """
    THE production entry point that turns a `PlacementDecision` + bound `WorkerNode` into
    live execution through the unmodified Group-1 boundary. See module docstring for the
    structural no-bypass guarantee (no `site_id` parameter exists here at all).

    Step order (each step's failure means the NEXT step, and all physical I/O, never
    happens):
      1. `decision.is_stale(...)` against a FRESH topology snapshot -- refuses before
         even issuing an assignment if topology drifted or the decision's TTL elapsed.
      2. `control_plane.issue_assignment(site_id=decision.selected_site_id, ...)` -- the
         unmodified Group-1 trust/tenant/fencing/authorization gate (SiteRegistry.
         assign_execution) runs here for free; a site revoked between placement and this
         call is caught right here, before any transport call.
      3. Assignment/decision binding integrity check (site_id + correlation_id match).
      3a. P7B.25 GROUP-3 MANDATORY-WHEN-CONFIGURED OWNERSHIP GATE: if `ownership_manager`
          is supplied, distributed execution ownership for this (tenant, migration, plan)
          unit of work is ACQUIRED here -- before any physical I/O -- bound to the exact
          site/worker/tenant/plan/plan_fingerprint/seal this `decision` already carries
          (never a caller-chosen alternative; there is no parameter on this function that
          lets a caller point ownership at a different site/tenant/plan than `decision`
          itself resolved). Acquisition failure (another valid owner, site no longer
          trusted, etc.) raises immediately and NO assignment is used, NO
          `execute_assignment_via_transport` call happens, and NO physical read/write is
          attempted. `ownership_manager=None` preserves every pre-existing caller's exact
          behavior (Group-1/Group-2's own hostile-tested test suites call this function
          directly with no Group-3 concept at all) -- but see
          `akaalPipeline.orchestration.fabric_gate`/`akaalPipeline.execution.coordinator`
          for why the PRODUCTION Pipeline seam never leaves this `None` for a
          fabric-required plan: mandatory-ness is enforced one layer up, at the boundary
          that actually knows whether Fabric placement (and therefore ownership) is
          required for this plan, exactly mirroring how Group-2 placement itself became
          mandatory without changing this function's own permissive default.
      4. `execute_assignment_via_transport(..., live_trust_check=<composed>)` -- the
         unmodified Group-1 physical-execution boundary, with a live_trust_check that
         ALSO re-verifies worker binding validity, topology freshness, (if supplied)
         residency, AND (if `ownership_manager` supplied) that ownership is STILL the
         current, unexpired, correctly-fenced generation -- on every one of
         TransportAuthority's own existing revalidation points (pre-read, pre-batch,
         pre-write) -- not a new mechanism, a richer composition of the existing one.
         Each such check RENEWS ownership (not merely validates it): a legitimate,
         long-running transfer keeps its own lease alive and re-confirms current site
         trust on every checkpoint, while a stale/superseded/expired owner is rejected
         the instant its captured lease_id/fencing_generation no longer matches current.
    """
    current_topology = current_topology_provider()
    if decision.is_stale(current_topology_fingerprint=current_topology.fingerprint()):
        raise StalePlacementError(
            f"PlacementDecision {decision.decision_id!r} is stale (expired or topology "
            f"drifted since decision time); refusing to issue an assignment against it. "
            f"Caller must re-run decide_placement."
        )

    assignment: RemoteExecutionAssignment = control_plane.issue_assignment(
        site_id=decision.selected_site_id,
        tenant_id=decision.tenant_id,
        workspace_id=decision.workspace_id,
        project_id=decision.project_id,
        migration_id=decision.migration_id,
        plan_id=decision.plan_id,
        plan_revision=decision.plan_revision,
        execution_identity_seal_fingerprint=decision.execution_identity_seal_fingerprint,
        fencing_epoch=decision.fencing_epoch,
        correlation_id=decision.correlation_id,
        authorization_callback=site_authorization_callback,
        signing_key=signing_key, signer=signer,
        ttl_minutes=assignment_ttl_minutes,
    )

    if assignment.site_id != decision.selected_site_id or assignment.correlation_id != decision.correlation_id:
        raise PlacementBindingIntegrityError(
            f"Issued assignment {assignment.assignment_id!r} (site={assignment.site_id!r}, "
            f"correlation_id={assignment.correlation_id!r}) does not match placement "
            f"decision {decision.decision_id!r} (site={decision.selected_site_id!r}, "
            f"correlation_id={decision.correlation_id!r}); refusing to execute a "
            f"substituted assignment."
        )

    bound_worker = worker  # captured by value at bind time; re-fetched live inside the check below

    ownership_record = None
    if ownership_manager is not None:
        ownership_claim = OwnershipClaim(
            tenant_id=decision.tenant_id, workspace_id=decision.workspace_id, project_id=decision.project_id,
            migration_id=decision.migration_id, plan_id=decision.plan_id,
            plan_fingerprint=decision.execution_identity_seal_fingerprint,
            execution_identity_seal_fingerprint=decision.execution_identity_seal_fingerprint,
            execution_id=execution_id or decision.decision_id,
            placement_id=decision.decision_id,
            assignment_id=assignment.assignment_id,
            site_id=decision.selected_site_id, worker_id=bound_worker.worker_id,
            correlation_id=decision.correlation_id, ttl_seconds=ownership_ttl_seconds,
        )
        # Acquired BEFORE any physical I/O -- a conflicting/ineligible ownership claim
        # (another valid owner, site no longer TRUSTED/tenant-bound, etc.) raises here and
        # execution never proceeds to execute_assignment_via_transport at all.
        try:
            ownership_record = ownership_manager.acquire(ownership_claim)
            assignment_consistent_with_ownership(
                ownership_record, assignment_site_id=assignment.site_id,
                assignment_tenant_id=assignment.tenant_id, assignment_plan_id=assignment.plan_id,
            )
        except OwnershipError as ownership_exc:
            # P7B.32/34 Telemetry/Evidence recording are post-hoc side effects, never a
            # gate -- the REAL rejection (ownership_exc) always propagates unchanged; a
            # broken telemetry/evidence backend must never mask or soften the real
            # security outcome (P7B Group-3 laws: "Telemetry != execution truth",
            # "Evidence != authorization").
            if evidence_authority is not None:
                try:
                    from akaalEngine.fabric.group3_evidence import emit_ownership_decision_evidence
                    emit_ownership_decision_evidence(
                        evidence_authority, migration_id=decision.migration_id, run_id=run_id or f"run-{assignment.assignment_id}",
                        ownership_key=ownership_claim.ownership_key(), tenant_id=decision.tenant_id,
                        site_id=decision.selected_site_id, worker_id=bound_worker.worker_id,
                        accepted=False, reason=str(ownership_exc),
                    )
                except Exception:  # noqa: BLE001 -- deliberate: evidence emission never overrides the real outcome
                    pass
            if telemetry_authority is not None:
                try:
                    from akaalEngine.fabric.telemetry_integration import ownership_event
                    telemetry_authority.record_event(ownership_event(
                        event_type="fabric.ownership.conflict_rejected", ownership_key=ownership_claim.ownership_key(),
                        tenant_id=decision.tenant_id, site_id=decision.selected_site_id, worker_id=bound_worker.worker_id,
                        fencing_generation=-1, correlation_id=decision.correlation_id, outcome=str(ownership_exc),
                    ))
                except Exception:  # noqa: BLE001 -- deliberate: telemetry never overrides the real outcome
                    pass
            raise
        if evidence_authority is not None:
            try:
                from akaalEngine.fabric.group3_evidence import emit_ownership_decision_evidence
                emit_ownership_decision_evidence(
                    evidence_authority, migration_id=decision.migration_id, run_id=run_id or f"run-{assignment.assignment_id}",
                    ownership_key=ownership_record.ownership_key, tenant_id=decision.tenant_id,
                    site_id=decision.selected_site_id, worker_id=bound_worker.worker_id,
                    accepted=True, fencing_generation=ownership_record.fencing_generation,
                )
            except Exception:  # noqa: BLE001 -- deliberate: see above
                pass
        if telemetry_authority is not None:
            try:
                from akaalEngine.fabric.telemetry_integration import ownership_event
                telemetry_authority.record_event(ownership_event(
                    event_type="fabric.ownership.acquired", ownership_key=ownership_record.ownership_key,
                    tenant_id=decision.tenant_id, site_id=decision.selected_site_id, worker_id=bound_worker.worker_id,
                    fencing_generation=ownership_record.fencing_generation, correlation_id=decision.correlation_id,
                    outcome="ACCEPTED",
                ))
            except Exception:  # noqa: BLE001 -- deliberate: telemetry never overrides the real outcome
                pass

    def composed_live_trust_check(a: RemoteExecutionAssignment) -> bool:
        if a.site_id != decision.selected_site_id or a.correlation_id != decision.correlation_id:
            return False
        live_topology = current_topology_provider()
        if decision.is_stale(current_topology_fingerprint=live_topology.fingerprint()):
            return False
        if residency_recheck is not None and residency_recheck() is not True:
            return False
        if not worker_still_valid(worker_registry, bound_worker):
            return False
        if ownership_manager is not None:
            try:
                assignment_consistent_with_ownership(
                    ownership_record, assignment_site_id=a.site_id,
                    assignment_tenant_id=a.tenant_id, assignment_plan_id=a.plan_id,
                )
                ownership_manager.renew(ownership_claim, ownership_record.lease_id, ownership_record.fencing_generation)
            except OwnershipError:
                return False
        if extra_live_trust_check is not None and extra_live_trust_check(a) is not True:
            return False
        return True

    try:
        result = execute_assignment_via_transport(
            transport_authority=transport_authority, assignment=assignment,
            signing_key=signing_key, verifier=verifier,
            expected_tenant_id=decision.tenant_id, expected_plan_id=decision.plan_id,
            expected_site_id=decision.selected_site_id, expected_seal_fingerprint=decision.execution_identity_seal_fingerprint,
            reader=reader, writer=writer, partition=partition,
            live_trust_check=composed_live_trust_check,
            route=route, current_edges_provider=current_edges_provider,
            evidence_authority=evidence_authority, run_id=run_id,
            **execute_kwargs,
        )
    finally:
        # Finalize the worker's lifecycle regardless of outcome -- this module makes no
        # assumption about whether the physical work succeeded or failed; that
        # determination belongs to the canonical runtime/checkpoint authorities, never
        # to this scheduling-adjacent layer. Delegated to the SAME canonical
        # finalize_worker_after_dispatch every other physical-effect capability now also
        # uses (see FabricPlacementExecutionPort) -- one worker-lifecycle finalization
        # point, not two.
        finalize_worker_after_dispatch(worker_registry, bound_worker, decision.tenant_id)

    return result
