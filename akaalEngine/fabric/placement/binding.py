"""
akaalEngine.fabric.placement.binding
========================================
P7B Group-2 production integration (post-review hardening) -- turns a Campaign C
placement decision into the canonical Group-1 execution boundary's inputs, and nothing
else. This module owns NO migration truth, NO transport, NO checkpoint/retry/CDC state --
it is the seam between `akaalEngine.fabric.placement.engine.evaluate_candidates`/
`akaalEngine.fabric.placement.optimize.rank_candidates` (Campaign C, unmodified) and
`akaalEngine.fabric.remote_execution.control_plane.RemoteExecutionControlPlane` (Group-1,
unmodified, frozen).

WHY THIS MODULE EXISTS: prior to this module, nothing in the production execution path
consumed a placement decision -- `RemoteExecutionControlPlane.issue_assignment` accepted
`site_id` as a bare caller-supplied parameter, meaning a caller could pick a site by any
means (or none) and Campaign C's topology/locality/capability/policy/residency/
optimization/cost reasoning would never be consulted. `decide_placement` below is the
ONLY function in this codebase that produces a `PlacementDecision`, and
`akaalEngine.fabric.placement.execution.execute_via_placement` is the ONLY function that
turns a `PlacementDecision` into a live `RemoteExecutionAssignment` + physical execution
-- there is no `site_id` parameter anywhere in `execute_via_placement`'s signature other
than the one embedded, read-only, inside the `PlacementDecision` it was handed (see
`akaalEngine.fabric.placement.execution` module docstring for the structural proof this
mirrors `k8s_runtime.pod_spec`'s missing-hostNetwork-parameter pattern).

FAIL-CLOSED LAW (P7B Group-2 §25/§30 of the original directive, now made load-bearing
rather than merely tested in isolation): if `evaluate_candidates` accepts zero
candidates, `decide_placement` raises `NoCompliantPlacementError` BEFORE constructing
anything -- no `RemoteExecutionAssignment` is issued, no `TransportAuthority` method is
ever called, no physical read/write/checkpoint can occur, because nothing downstream of
this function can run without the `PlacementDecision` it refused to produce.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.locality.models import LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.placement.capability import CapabilityRequirement, CapacityOffer
from akaalEngine.fabric.placement.cost import CostEstimate
from akaalEngine.fabric.placement.engine import PlacementEvaluationResult, evaluate_candidates
from akaalEngine.fabric.placement.optimize import rank_candidates
from akaalEngine.fabric.placement.policy import PlacementAuthorizationCallback
from akaalEngine.fabric.placement.residency import ResidencyPolicy
from akaalEngine.fabric.topology.graph import TopologyGraph


class PlacementBindingError(ValueError):
    pass


class NoCompliantPlacementError(PlacementBindingError):
    """Raised when zero candidates survive capability/authorization/residency filtering.
    Callers MUST treat this as a hard stop -- there is no fallback candidate list to
    retry with inside this module, and no caller of `decide_placement` anywhere in this
    codebase is permitted to catch this and substitute an unfiltered site (doing so would
    silently reintroduce exactly the bypass this module exists to close)."""

    def __init__(self, plan_reference: str, evaluation: PlacementEvaluationResult) -> None:
        self.plan_reference = plan_reference
        self.evaluation = evaluation
        super().__init__(
            f"NO COMPLIANT PLACEMENT for {plan_reference!r}: {len(evaluation.rejected)} "
            f"candidate(s) evaluated, 0 accepted. Rejection reasons: "
            + "; ".join(f"{r.site_id}[{r.stage}]: {', '.join(r.reasons)}" for r in evaluation.rejected)
        )


class StalePlacementError(PlacementBindingError):
    """Raised when a PlacementDecision has expired or the topology it was decided
    against has drifted since decision time."""


@dataclass(frozen=True)
class PlacementDecision:
    """
    Immutable record of ONE placement decision. This is not a second ExecutionPlan --
    it carries only an opaque reference to the plan (`plan_id`/`plan_revision`/
    `execution_identity_seal_fingerprint`, all caller-supplied, never re-derived) plus the
    fields specific to WHERE execution was placed and WHY. `correlation_id` is the sole
    binding key threaded into the Group-1 `RemoteExecutionAssignment.correlation_id`
    field (already existing, unmodified) -- see `execution.execute_via_placement` for how
    that binding is re-verified at execution time.
    """
    decision_id: str
    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_revision: int
    execution_identity_seal_fingerprint: str
    correlation_id: str
    selected_site_id: str
    topology_fingerprint: str
    fencing_epoch: int
    plan_reference: str
    acceptance_reasons: Tuple[str, ...]
    rejected_candidate_count: int
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat())

    def __post_init__(self) -> None:
        for name in ("decision_id", "tenant_id", "workspace_id", "project_id", "migration_id",
                     "plan_id", "correlation_id", "selected_site_id", "topology_fingerprint", "plan_reference"):
            if not getattr(self, name) or not str(getattr(self, name)).strip():
                raise PlacementBindingError(f"PlacementDecision.{name} must be non-empty.")
        if self.fencing_epoch < 1:
            raise PlacementBindingError("PlacementDecision.fencing_epoch must be >= 1.")

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        current = now or datetime.now(timezone.utc)
        expiry = datetime.fromisoformat(self.expires_at)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return current >= expiry

    def is_stale(self, *, current_topology_fingerprint: str, now: Optional[datetime] = None) -> bool:
        """Mirrors MovementRoute.is_stale_against()/TopologyGraph.is_stale_against() at
        the placement-decision level: expired TTL OR topology drift since decision time
        both count as stale. A caller finding this True must re-run `decide_placement`
        from scratch -- there is no partial/incremental repair path."""
        if self.is_expired(now):
            return True
        return self.topology_fingerprint != current_topology_fingerprint


def decide_placement(
    *,
    tenant_id: str,
    workspace_id: str,
    project_id: str,
    migration_id: str,
    plan_id: str,
    plan_revision: int,
    execution_identity_seal_fingerprint: str,
    fencing_epoch: int,
    candidates: List[ExecutionSite],
    capability_requirement: CapabilityRequirement,
    capacity_by_site: Optional[Mapping[str, CapacityOffer]] = None,
    actor_context: Any,
    authorization_action: str = "assign_execution",
    authorization_callback: Optional[PlacementAuthorizationCallback],
    authorization_context: Optional[Mapping[str, Any]] = None,
    residency_policies: Tuple[ResidencyPolicy, ...] = (),
    locality_by_site: Optional[Mapping[str, Mapping[LocalitySubjectRole, LocalityRecord]]] = None,
    topology_graph: TopologyGraph,
    cost_by_site: Optional[Mapping[str, CostEstimate]] = None,
    proximity_score_by_site: Optional[Mapping[str, float]] = None,
    load_score_by_site: Optional[Mapping[str, float]] = None,
    correlation_id: Optional[str] = None,
    decision_ttl_minutes: float = 10.0,
) -> PlacementDecision:
    """
    THE production entry point for Campaign C. Runs capability -> authorization ->
    residency filtering (`placement.engine.evaluate_candidates`, unmodified), then ranks
    the accepted set (`placement.optimize.rank_candidates`, unmodified), and binds the
    winner into an auditable, fingerprint-stamped `PlacementDecision`.

    `topology_graph` is a snapshot the CALLER already took (from
    `TopologyRegistry.snapshot(tenant_id)`) -- this function never queries a registry
    itself (no hidden I/O, no registry dependency baked in), it only reads
    `topology_graph.fingerprint()` to stamp the decision for later staleness detection.

    Raises `NoCompliantPlacementError` (see class docstring) if zero candidates survive
    filtering -- this is the ENTIRE mechanism by which "NO COMPLIANT PLACEMENT" becomes
    load-bearing rather than a documented-but-optional outcome: there is no way to obtain
    a `PlacementDecision` object when this condition is hit, and every downstream
    function in this package requires one.
    """
    evaluation = evaluate_candidates(
        plan_reference=capability_requirement.plan_reference,
        candidates=candidates,
        capability_requirement=capability_requirement,
        capacity_by_site=capacity_by_site,
        actor_context=actor_context,
        authorization_action=authorization_action,
        authorization_callback=authorization_callback,
        authorization_context=authorization_context,
        residency_policies=residency_policies,
        locality_by_site=locality_by_site,
        tenant_id=tenant_id,
    )

    if not evaluation.has_compliant_placement():
        raise NoCompliantPlacementError(capability_requirement.plan_reference, evaluation)

    accepted_ids = tuple(a.site_id for a in evaluation.accepted)
    ranked = rank_candidates(
        accepted_ids, cost_by_site=cost_by_site,
        proximity_score_by_site=proximity_score_by_site, load_score_by_site=load_score_by_site,
    )
    winner = ranked[0]
    winner_acceptance = next(a for a in evaluation.accepted if a.site_id == winner.site_id)

    return PlacementDecision(
        decision_id=f"placement-{uuid.uuid4().hex[:16]}",
        tenant_id=tenant_id, workspace_id=workspace_id, project_id=project_id,
        migration_id=migration_id, plan_id=plan_id, plan_revision=plan_revision,
        execution_identity_seal_fingerprint=execution_identity_seal_fingerprint,
        correlation_id=correlation_id or f"corr-{uuid.uuid4().hex[:16]}",
        selected_site_id=winner.site_id,
        topology_fingerprint=topology_graph.fingerprint(),
        fencing_epoch=fencing_epoch,
        plan_reference=capability_requirement.plan_reference,
        acceptance_reasons=winner_acceptance.reasons,
        rejected_candidate_count=len(evaluation.rejected),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=decision_ttl_minutes)).isoformat(),
    )
