"""akaalEngine.intelligence.producers.strategy_generation
===========================================================
P7C.8 -- Multi-Objective Strategy Generation. Deterministic, analytical (never
model-fabricated) multi-objective scoring over a small set of candidate migration
strategy shapes. Security/residency/capability constraints define the FEASIBLE SET
and are applied before optimization -- an infeasible candidate is excluded, never
merely penalized (P7C brief §P7C.8 "Mandatory constraints before optimization").

This producer never emits an ExecutionPlan or canonical configuration -- its
output is a ranked set of StrategyCandidate proposals for canonical planning to
validate/compile, exactly per the P7C brief's critical pathway.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Mapping, Optional, Tuple

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    CounterfactualExplanation,
    EpistemicType,
    Explanation,
    IntelligenceResult,
    OptimizationAlternative,
    OptimizationResult,
)


class StrategyObjective(str, enum.Enum):
    FASTEST = "FASTEST"
    LOWEST_COST = "LOWEST_COST"
    LOWEST_DOWNTIME = "LOWEST_DOWNTIME"
    LOWEST_OPERATIONAL_RISK = "LOWEST_OPERATIONAL_RISK"
    LOWEST_RESOURCE_USAGE = "LOWEST_RESOURCE_USAGE"
    MAXIMUM_REVERSIBILITY = "MAXIMUM_REVERSIBILITY"
    DATA_LOCAL = "DATA_LOCAL"
    BALANCED = "BALANCED"


# Each dimension is normalized so that HIGHER is always BETTER for that dimension,
# and each objective's weight vector says how much it cares about each dimension.
# This keeps ranking a single deterministic dot-product, no hidden asymmetry.
_DIMENSIONS = ("speed", "cost_efficiency", "uptime", "safety", "resource_efficiency", "reversibility", "data_locality")

_OBJECTIVE_WEIGHTS: Dict[StrategyObjective, Dict[str, float]] = {
    StrategyObjective.FASTEST: {"speed": 1.0},
    StrategyObjective.LOWEST_COST: {"cost_efficiency": 1.0},
    StrategyObjective.LOWEST_DOWNTIME: {"uptime": 1.0},
    StrategyObjective.LOWEST_OPERATIONAL_RISK: {"safety": 1.0},
    StrategyObjective.LOWEST_RESOURCE_USAGE: {"resource_efficiency": 1.0},
    StrategyObjective.MAXIMUM_REVERSIBILITY: {"reversibility": 1.0},
    StrategyObjective.DATA_LOCAL: {"data_locality": 1.0},
    StrategyObjective.BALANCED: {d: 1.0 / len(_DIMENSIONS) for d in _DIMENSIONS},
}


@dataclass(frozen=True)
class StrategyCandidate:
    label: str
    parallelism_workers: int
    validation_depth: str  # "SAMPLED" | "FULL"
    region: str
    scores: Mapping[str, float]  # each dimension in [0.0, 1.0], higher = better

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "parallelism_workers": self.parallelism_workers,
            "validation_depth": self.validation_depth,
            "region": self.region,
            "scores": dict(self.scores),
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def generate_candidate_shapes(*, base_risk_score: float, allowed_regions: Tuple[str, ...]) -> List[StrategyCandidate]:
    """Generates a deterministic set of candidate strategy shapes, one per
    (parallelism shape x candidate region) combination in `allowed_regions` --
    `allowed_regions` here names the regions candidates are GENERATED for (a
    caller may propose candidates spanning several regions before the feasible-
    set filter narrows them down; see make_strategy_generation_producer). Higher
    parallelism trades cost/resource efficiency for speed/uptime; deeper
    validation trades some speed for safety. `base_risk_score` (0..1, higher =
    riskier, e.g. normalized from a P7C.7 StructuralRiskReport) pulls every
    candidate's safety score down proportionally -- a risky schema never gets an
    artificially high safety score regardless of shape."""
    regions = allowed_regions if allowed_regions else ("default",)
    safety_ceiling = _clamp01(1.0 - base_risk_score)

    shapes = [
        ("conservative_low_parallelism", 2, "FULL"),
        ("balanced_medium_parallelism", 8, "FULL"),
        ("aggressive_high_parallelism", 32, "SAMPLED"),
    ]
    candidates: List[StrategyCandidate] = []
    for region in regions:
        for label, workers, validation_depth in shapes:
            speed = _clamp01(workers / 32.0)
            uptime = _clamp01(0.3 + 0.6 * (workers / 32.0))
            cost_efficiency = _clamp01(1.0 - (workers / 32.0) * 0.7)
            resource_efficiency = _clamp01(1.0 - (workers / 32.0) * 0.8)
            validation_bonus = 0.15 if validation_depth == "FULL" else 0.0
            safety = _clamp01(safety_ceiling * (0.7 + validation_bonus))
            reversibility = _clamp01(0.9 - (workers / 32.0) * 0.3)
            data_locality = 1.0

            candidates.append(
                StrategyCandidate(
                    label=f"{label}__{region}",
                    parallelism_workers=workers,
                    validation_depth=validation_depth,
                    region=region,
                    scores={
                        "speed": speed,
                        "cost_efficiency": cost_efficiency,
                        "uptime": uptime,
                        "safety": safety,
                        "resource_efficiency": resource_efficiency,
                        "reversibility": reversibility,
                        "data_locality": data_locality,
                    },
                )
            )
    return candidates


def _score_for_objective(candidate: StrategyCandidate, objective: StrategyObjective) -> float:
    weights = _OBJECTIVE_WEIGHTS[objective]
    return sum(weights.get(dim, 0.0) * candidate.scores.get(dim, 0.0) for dim in _DIMENSIONS)


def compute_pareto_frontier(candidates: List[StrategyCandidate]) -> List[StrategyCandidate]:
    """Real Pareto-dominance computation: a candidate is excluded from the frontier
    only if another candidate is at least as good on EVERY dimension and strictly
    better on at least one."""
    frontier: List[StrategyCandidate] = []
    for c in candidates:
        dominated = False
        for other in candidates:
            if other is c:
                continue
            at_least_as_good = all(other.scores[d] >= c.scores[d] for d in _DIMENSIONS)
            strictly_better = any(other.scores[d] > c.scores[d] for d in _DIMENSIONS)
            if at_least_as_good and strictly_better:
                dominated = True
                break
        if not dominated:
            frontier.append(c)
    return frontier


def make_strategy_generation_producer():
    """Returns an IntelligenceKernel-compatible producer for IntelligenceTask.OPTIMIZE.

    request.parameters:
      - objective: str (StrategyObjective value), default BALANCED
      - base_risk_score: float in [0,1], default 0.0
      - allowed_regions: list[str] -- the FEASIBLE SET residency constraint; a
        candidate whose region is not in this list is excluded before scoring,
        never merely down-ranked.
      - candidate_regions: list[str], default ["default"] -- the region(s)
        candidate strategies are proposed for; the feasible-set filters below
        then narrow this down to `allowed_regions` AND `required_capability`.
      - required_capability: str, optional -- a capability the migration needs
        (e.g. "cdc_apply"). If given, `region_capability_map` MUST also be
        given (caller-supplied canonical capability facts -- this producer
        never invents which region supports what); a region missing the
        capability is excluded from the feasible set before scoring, exactly
        like an illegal region, never merely down-ranked.
      - region_capability_map: Mapping[str, list[str]], optional -- canonical
        capability facts per region, supplied by the caller (in production,
        derived from real P7B/provider capability truth -- this producer does
        not fabricate it).
      - constraints_fingerprint / current fingerprint staleness: if
        `constraints_generated_against_fingerprint` is supplied, it MUST match
        `context.canonical_state_fingerprint` (via the context's own dimension,
        not re-derived here) -- a caller optimizing against a stale constraint
        snapshot (e.g. residency policy changed since constraints were pulled)
        is refused, never silently optimized against outdated constraints.
    """

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        from akaalEngine.intelligence.models.errors import IntelligenceValidationError

        objective = StrategyObjective(str(request.parameters.get("objective", "BALANCED")).upper())
        base_risk_score = _clamp01(float(request.parameters.get("base_risk_score", 0.0)))
        allowed_regions = request.parameters.get("allowed_regions")
        required_capability = request.parameters.get("required_capability")
        region_capability_map = request.parameters.get("region_capability_map")
        candidate_regions = tuple(request.parameters.get("candidate_regions") or [request.parameters.get("candidate_region", "default")])

        # Staleness gate: a constraint snapshot bound to a canonical-state
        # fingerprint that no longer matches current context must never be
        # silently optimized against (P7C brief "staleness/revalidation").
        constraints_fp = request.parameters.get("constraints_generated_against_fingerprint")
        if constraints_fp is not None and constraints_fp != context.canonical_state_fingerprint:
            raise IntelligenceValidationError(
                f"Feasibility constraints were generated against canonical-state fingerprint "
                f"{constraints_fp!r}, which no longer matches current context fingerprint "
                f"{context.canonical_state_fingerprint!r}; refusing to optimize against stale constraints."
            )

        if required_capability is not None and region_capability_map is None:
            raise IntelligenceValidationError(
                "request.parameters['required_capability'] was supplied without "
                "'region_capability_map'; refusing to guess capability compatibility."
            )

        raw_candidates = generate_candidate_shapes(base_risk_score=base_risk_score, allowed_regions=candidate_regions)

        counterfactuals: List[CounterfactualExplanation] = []
        feasible = raw_candidates
        excluded_by_residency_labels: List[str] = []
        excluded_by_capability_labels: List[str] = []

        if allowed_regions is not None:
            allowed_regions_set: FrozenSet[str] = frozenset(str(r) for r in allowed_regions)
            excluded = [c for c in feasible if c.region not in allowed_regions_set]
            feasible = [c for c in feasible if c.region in allowed_regions_set]
            excluded_by_residency_labels = [c.label for c in excluded]
            for c in excluded:
                counterfactuals.append(
                    CounterfactualExplanation(
                        rejected_alternative=c.label,
                        blocking_constraint=f"residency_policy:allowed_regions={sorted(allowed_regions_set)}",
                        would_require_change=f"residency policy would need to permit region {c.region!r}",
                    )
                )

        if required_capability is not None:
            capability_map = {str(k): frozenset(str(v) for v in vs) for k, vs in dict(region_capability_map).items()}
            excluded = [c for c in feasible if str(required_capability) not in capability_map.get(c.region, frozenset())]
            feasible = [c for c in feasible if str(required_capability) in capability_map.get(c.region, frozenset())]
            excluded_by_capability_labels = [c.label for c in excluded]
            for c in excluded:
                counterfactuals.append(
                    CounterfactualExplanation(
                        rejected_alternative=c.label,
                        blocking_constraint=f"capability_policy:required_capability={required_capability!r}",
                        would_require_change=f"region {c.region!r} would need to support capability {required_capability!r}",
                    )
                )

        if not feasible:
            raise IntelligenceValidationError(
                "No strategy candidate satisfies the required residency/capability constraints; "
                "refusing to optimize an empty feasible set."
            )

        ranked = sorted(feasible, key=lambda c: (-_score_for_objective(c, objective), c.label))
        pareto = compute_pareto_frontier(feasible)

        alternatives = [
            OptimizationAlternative(
                label=c.label,
                objective_scores={o.value: round(_score_for_objective(c, o), 4) for o in StrategyObjective},
                rationale=f"parallelism={c.parallelism_workers}, validation_depth={c.validation_depth}, "
                f"on_pareto_frontier={c in pareto}",
            )
            for c in ranked
        ]

        best = ranked[0]
        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.RECOMMENDATION,
            summary=f"Recommended strategy for objective {objective.value}: {best.label} "
            f"({best.parallelism_workers} workers, {best.validation_depth} validation).",
            explanation=Explanation(
                summary="Ranked by deterministic weighted multi-objective scoring over feasible candidates.",
                supporting_facts=[f"{len(feasible)} feasible candidates evaluated", f"{len(pareto)} on Pareto frontier"],
                alternatives_considered=[c.label for c in ranked[1:]],
                counterfactuals=counterfactuals,
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=len(feasible) / len(raw_candidates)),
            optimization=OptimizationResult(objective=objective.value, alternatives=alternatives),
            data={
                "pareto_frontier": [c.to_dict() for c in pareto],
                "excluded_by_residency": excluded_by_residency_labels,
                "excluded_by_capability": excluded_by_capability_labels,
            },
        )

    return producer
