"""akaalEngine.intelligence.producers.optimization
=====================================================
P7C.16 -- Performance & Resource Optimization. Reuses P7C.12's
evaluate_scenario/CutoverScenario arithmetic (akaalEngine.intelligence.
producers.capacity_simulation -- "no duplicate prediction authorities") for
duration/feasibility, and P7C.8's trusted canonical constraint projection
(akaalEngine.intelligence.knowledge.constraint_projection -- the SAME
CANONICAL_FEASIBLE_SET ∩ CALLER_REQUESTED_SET discipline, never a second
residency/capability authority) to guarantee an illegal region can never win
as a recommended alternative.

Cost is computed only from a caller-SUPPLIED cost_per_worker_hour (the
organization's own configured rate) -- never an invented price catalog
(P7C.20 discipline applies here too, since optimization already touches cost
as one objective dimension).
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from akaalEngine.intelligence.knowledge.constraint_projection import TrustedStrategyConstraintSnapshot
from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.errors import IntelligenceValidationError
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
from akaalEngine.intelligence.producers.capacity_simulation import evaluate_scenario

# Deliberately the SAME resolver type P7C.8's strategy_generation already
# consumes (akaalPipeline.application.unified_caller.PipelineUnifiedCaller.
# _build_strategy_constraint_resolver) -- reusing it here means P7C.16 gets
# real per-ACTOR (not merely per-tenant) canonical authorization, built from
# THIS exact request's real authenticated actor identity/roles (threaded via
# IntelligenceContext.extra_dimensions), with zero new authorization
# mechanism. Never a second region/capability authority.
ConstraintResolver = Callable[[IntelligenceRequest, IntelligenceContext], TrustedStrategyConstraintSnapshot]


def make_optimization_producer(constraint_resolver: Optional[ConstraintResolver] = None):
    """`constraint_resolver` -- if given, MUST be backed by a REAL trusted,
    per-actor authorization decision-maker (in production, akaalPipeline.
    application.unified_caller.PipelineUnifiedCaller._build_strategy_
    constraint_resolver -- the exact same one P7C.8 uses). Without it, any
    request asserting `candidate_regions` refuses rather than trusting
    caller-only region claims (fail closed)."""

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        params = request.parameters
        required = ["dataset_size_bytes", "worker_throughput_bytes_per_sec", "validation_throughput_bytes_per_sec", "cutover_window_seconds"]
        missing = [k for k in required if k not in params]
        if missing:
            raise IntelligenceValidationError(f"Optimization missing required parameters: {missing}.")

        worker_counts: List[int] = list(params.get("candidate_worker_counts") or [4, 8, 16])
        cost_per_worker_hour = params.get("cost_per_worker_hour")
        candidate_regions = params.get("candidate_regions")

        legal_regions: Optional[frozenset] = None
        counterfactuals: List[CounterfactualExplanation] = []
        if candidate_regions:
            if constraint_resolver is None:
                raise IntelligenceValidationError(
                    "Optimization requested region-scoped candidates (candidate_regions) but no canonical "
                    "region authorization decision-maker is configured. Refusing to trust caller-only region claims."
                )
            snapshot = constraint_resolver(request, context)
            legal_regions = snapshot.allowed_regions
            for region in candidate_regions:
                if region not in legal_regions:
                    counterfactuals.append(
                        CounterfactualExplanation(
                            rejected_alternative=f"region={region}",
                            blocking_constraint="Canonical authorization does not grant this tenant this region.",
                            would_require_change="Tenant would need a canonical region grant for this region before it could be evaluated.",
                        )
                    )

        scenarios = [
            evaluate_scenario(
                label=f"{wc}_workers",
                dataset_size_bytes=float(params["dataset_size_bytes"]),
                worker_throughput_bytes_per_sec=float(params["worker_throughput_bytes_per_sec"]),
                worker_count=int(wc),
                validation_throughput_bytes_per_sec=float(params["validation_throughput_bytes_per_sec"]),
                cutover_window_seconds=float(params["cutover_window_seconds"]),
                cdc_backlog_bytes=float(params.get("cdc_backlog_bytes", 0.0)),
                cdc_generation_rate_bytes_per_sec=float(params.get("cdc_generation_rate_bytes_per_sec", 0.0)),
                cdc_apply_rate_bytes_per_sec=float(params.get("cdc_apply_rate_bytes_per_sec", 0.0)),
            )
            for wc in worker_counts
        ]

        alternatives = []
        for s in scenarios:
            scores: dict = {"feasible": 1.0 if s.is_feasible else 0.0}
            if s.total_point_seconds is not None:
                scores["duration_seconds"] = s.total_point_seconds
                if cost_per_worker_hour is not None:
                    duration_hours = s.total_point_seconds / 3600.0
                    scores["cost"] = float(cost_per_worker_hour) * s.worker_count * duration_hours
            alternatives.append(
                OptimizationAlternative(
                    label=s.label,
                    objective_scores=scores,
                    rationale=(
                        "Backlog never converges at current generation/apply rates." if s.cdc_catchup_duration is None
                        else ("Fits cutover window." if s.is_feasible else "Exceeds cutover window.")
                    ),
                )
            )

        feasible_alternatives = [a for a in alternatives if a.objective_scores.get("feasible") == 1.0]
        # Hard constraints dominate: an alternative that is not cutover-feasible,
        # or whose region was canonically rejected, is never presented as "best"
        # regardless of how good its cost/duration numbers look.
        best = None
        if feasible_alternatives:
            scored = [a for a in feasible_alternatives if "duration_seconds" in a.objective_scores]
            if scored:
                best = min(scored, key=lambda a: a.objective_scores["duration_seconds"]).label

        summary = (
            f"{len(scenarios)} candidate(s) evaluated, {len(feasible_alternatives)} feasible within cutover window"
            + (f"; best={best}" if best else "")
            + (f"; {len(counterfactuals)} region candidate(s) rejected by canonical authorization" if counterfactuals else "")
            + "."
        )

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.RECOMMENDATION,
            summary=summary,
            explanation=Explanation(
                summary="Deterministic scenario arithmetic (reused from P7C.12) filtered through the SAME "
                "trusted canonical region/capability projection as P7C.8 -- an illegal candidate can never win.",
                supporting_facts=[f"candidate_worker_counts={worker_counts}"],
                counterfactuals=counterfactuals,
            ),
            confidence_evidence=ConfidenceEvidence(
                evidence_coverage=1.0 if not candidate_regions or constraint_resolver is not None else 0.0,
                missing_information=(
                    [] if cost_per_worker_hour is not None
                    else ["cost_per_worker_hour not supplied -- cost objective omitted, never estimated from an invented price."]
                ),
            ),
            optimization=OptimizationResult(objective="DURATION_COST_TRADEOFF", alternatives=alternatives),
            data={
                "scenarios": [s.to_dict() for s in scenarios],
                "best_alternative": best,
                "legal_regions": sorted(legal_regions) if legal_regions is not None else None,
            },
        )

    return producer
