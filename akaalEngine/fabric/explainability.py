"""
akaalEngine.fabric.explainability
====================================
P7B.33 -- Topology & Placement Explainability.

Deterministic, truthful rendering of decisions ALREADY MADE by the UNMODIFIED Group-2
`akaalEngine.fabric.placement.engine.evaluate_candidates` and P7B.28
`akaalEngine.fabric.failover.attempt_failover` -- this module creates NO second decision
engine and computes nothing new. Every function here is a PURE, stateless formatter over
an already-produced, immutable decision artifact (`PlacementEvaluationResult`/
`FailoverResult`); there is no global/shared mutable state anywhere in this module, so one
caller's explanation request can never be contaminated by another's (the concrete "cross-
tenant leakage" proof in
tests/unit/engine_fabric/test_p7b33_explainability.py::
test_two_tenants_explanations_never_cross_contaminate rests on exactly this purity).

EXPLANATION != AUTHORITY (P7B Group-3 law): calling any function here has no side effect
on placement/ownership/failover state, and the returned structure is informational only --
nothing reads it back to make a subsequent decision.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from akaalEngine.fabric.failover.models import FailoverResult
from akaalEngine.fabric.placement.engine import PlacementEvaluationResult


def explain_placement(result: PlacementEvaluationResult) -> Dict[str, Any]:
    """
    Renders exactly what `evaluate_candidates` decided -- no field here is computed from
    anything other than `result` itself. `rejected` entries carry only the structured
    stage ("CAPABILITY"/"AUTHORIZATION"/"RESIDENCY") and the reasons the real evaluators
    already produced -- never raw policy configuration, and never a candidate that did not
    actually appear in `result.accepted`/`result.rejected`.
    """
    return {
        "plan_reference": result.plan_reference,
        "compliant": result.has_compliant_placement(),
        "accepted": tuple({"site_id": a.site_id, "reasons": a.reasons} for a in result.accepted),
        "rejected": tuple({"site_id": r.site_id, "stage": r.stage, "reasons": r.reasons} for r in result.rejected),
    }


def explain_ownership_decision(
    *,
    accepted: bool,
    ownership_key: str,
    tenant_id: str,
    site_id: str,
    worker_id: str,
    capability: str,
    fencing_generation: Optional[int] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Renders exactly what `akaalEngine.fabric.ownership.OwnershipManager.acquire` (via
    `akaalEngine.fabric.placement.execution.acquire_ownership_for_physical_capability`)
    decided for one physical-effect capability dispatch, at the production
    `PlanExecutionCoordinator` ownership gate -- every field here is a value the caller
    (in production, `PlanExecutionCoordinator._acquire_ownership_gate`) already had in
    hand from the real decision; nothing is inferred or fabricated. `reason` is the raw
    `str(OwnershipError)` message on rejection (a safe, human-readable string, never a
    stack trace or secret-shaped value -- OwnershipError messages only ever interpolate
    identifiers/state names, per akaalEngine.fabric.ownership.manager's own discipline).
    """
    return {
        "decision_type": "ownership",
        "accepted": accepted,
        "ownership_key": ownership_key,
        "tenant_id": tenant_id,
        "site_id": site_id,
        "worker_id": worker_id,
        "capability": capability,
        "fencing_generation": fencing_generation,
        "reason": reason,
    }


def explain_failover(result: FailoverResult) -> Dict[str, Any]:
    """
    Renders exactly what `attempt_failover` decided. `placement_explanation` is None when
    `attempt_failover` never reached the placement-evaluation step (outcome NOT_REQUIRED)
    -- this is the truthful state, never backfilled with a fabricated "would have been"
    narrative.
    """
    return {
        "outcome": result.outcome.value,
        "old_ownership_key": result.old_ownership_key,
        "old_site_id": result.old_record.site_id if result.old_record is not None else None,
        "old_fencing_generation": result.old_record.fencing_generation if result.old_record is not None else None,
        "selected_site_id": result.selected_site_id,
        "new_fencing_generation": result.new_record.fencing_generation if result.new_record is not None else None,
        "reasons": result.reasons,
        "placement_explanation": explain_placement(result.placement_result) if result.placement_result is not None else None,
    }
