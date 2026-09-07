"""
akaalEngine.fabric.placement.engine
======================================
P7B.13-15 composition -- NOT a new scheduling/migration authority.

This module is a pure, stateless composition point that enforces the mandatory ordering:

    CAPABILITY (P7B.13) -> AUTHORIZATION (P7B.14) -> RESIDENCY (P7B.15)

A candidate rejected at any stage is never evaluated by a later stage and can never be
resurrected by one -- there is no scoring or optimization here at all (that is P7B.16,
layered strictly above this module's output, and it may only ever rank candidates this
module already accepted, never override a rejection). If zero candidates survive all
three stages, `evaluate_candidates` returns an empty accepted list -- callers MUST treat
that as NO COMPLIANT PLACEMENT and must never fall back to an unfiltered or partially-
filtered candidate merely to preserve availability (see
akaalEngine.fabric.placement.residency module docstring: "residency restrictions survive
failover").

This module owns NONE of: migration truth, ExecutionPlan, transport, checkpointing,
authorization decisions, residency policy authorship. It only calls the real
capability/policy/residency evaluators (P7B.13/14/15) in the correct order and shapes
their combined, explainable output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Tuple

from akaalEngine.fabric.execution_site.models import ExecutionSite
from akaalEngine.fabric.locality.models import LocalityRecord, LocalitySubjectRole
from akaalEngine.fabric.placement.capability import CapabilityRequirement, CapacityOffer, evaluate_capability
from akaalEngine.fabric.placement.policy import PlacementAuthorizationCallback, evaluate_policy
from akaalEngine.fabric.placement.residency import ResidencyPolicy, evaluate_residency


class PlacementEngineError(ValueError):
    pass


@dataclass(frozen=True)
class CandidateRejection:
    site_id: str
    stage: str  # "CAPABILITY" | "AUTHORIZATION" | "RESIDENCY"
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class CandidateAcceptance:
    site_id: str
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class PlacementEvaluationResult:
    plan_reference: str
    accepted: Tuple[CandidateAcceptance, ...]
    rejected: Tuple[CandidateRejection, ...]

    def has_compliant_placement(self) -> bool:
        return len(self.accepted) > 0


def evaluate_candidates(
    *,
    plan_reference: str,
    candidates: List[ExecutionSite],
    capability_requirement: CapabilityRequirement,
    capacity_by_site: Optional[Mapping[str, CapacityOffer]] = None,
    actor_context: Any,
    authorization_action: str,
    authorization_callback: Optional[PlacementAuthorizationCallback],
    authorization_context: Optional[Mapping[str, Any]] = None,
    residency_policies: Tuple[ResidencyPolicy, ...] = (),
    locality_by_site: Optional[Mapping[str, Mapping[LocalitySubjectRole, LocalityRecord]]] = None,
    tenant_id: Optional[str] = None,
) -> PlacementEvaluationResult:
    """
    Evaluates every candidate through CAPABILITY -> AUTHORIZATION -> RESIDENCY, in that
    fixed order, per candidate. `residency_policies` is a tuple because a real deployment
    may need to check more than one independent residency rule (e.g. "India-only" AND "no
    unapproved jurisdiction transit") -- a candidate must satisfy ALL supplied policies.

    `capacity_by_site` and `locality_by_site` are optional lookups keyed by site_id;
    a missing entry is treated exactly as if `None`/empty had been passed for that site
    (capability evaluation refuses to assume sufficient capacity; residency evaluation
    for a role with no record fails closed) -- never silently skipped.

    `tenant_id`, when supplied, is threaded into every `evaluate_residency` call as
    `expected_tenant_id` -- closing the "cross-tenant locality object" hostile scenario
    (a LocalityRecord genuinely proven for a DIFFERENT tenant must never silently satisfy
    this tenant's residency policy merely because a caller placed it under the right
    dict key). Production callers (`akaalEngine.fabric.placement.binding.decide_placement`)
    always supply it; it remains optional here only for backward compatibility with
    existing Campaign-C-only callers that pre-date this check and do not yet route
    tenant-scoped locality data through this function.
    """
    if not plan_reference or not plan_reference.strip():
        raise PlacementEngineError("evaluate_candidates requires a non-empty plan_reference.")

    accepted: List[CandidateAcceptance] = []
    rejected: List[CandidateRejection] = []
    capacity_by_site = capacity_by_site or {}
    locality_by_site = locality_by_site or {}

    for site in candidates:
        cap_eval = evaluate_capability(site, capability_requirement, capacity_by_site.get(site.site_id))
        if not cap_eval.satisfied:
            rejected.append(CandidateRejection(site_id=site.site_id, stage="CAPABILITY", reasons=cap_eval.reasons))
            continue

        policy_eval = evaluate_policy(
            site, actor_context, action=authorization_action,
            authorization_callback=authorization_callback, context=authorization_context,
        )
        if not policy_eval.permitted:
            rejected.append(CandidateRejection(site_id=site.site_id, stage="AUTHORIZATION", reasons=policy_eval.reasons))
            continue

        residency_reasons: List[str] = []
        residency_failed = False
        for policy in residency_policies:
            locality_map = locality_by_site.get(site.site_id, {})
            res_eval = evaluate_residency(policy, locality_map, expected_tenant_id=tenant_id)
            if not res_eval.compliant:
                residency_failed = True
                residency_reasons.extend(f"policy {policy.policy_id!r}: {v.role.value} -- {v.reason}" for v in res_eval.violations)
            else:
                residency_reasons.extend(res_eval.reasons)
        if residency_failed:
            rejected.append(CandidateRejection(site_id=site.site_id, stage="RESIDENCY", reasons=tuple(residency_reasons)))
            continue

        accepted.append(CandidateAcceptance(
            site_id=site.site_id,
            reasons=cap_eval.reasons + policy_eval.reasons + tuple(residency_reasons),
        ))

    return PlacementEvaluationResult(plan_reference=plan_reference, accepted=tuple(accepted), rejected=tuple(rejected))
