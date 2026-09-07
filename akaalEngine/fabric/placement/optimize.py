"""
akaalEngine.fabric.placement.optimize
========================================
P7B.16 -- Placement Optimization.

Ranks candidates that ALREADY SURVIVED akaalEngine.fabric.placement.engine.evaluate_
candidates (capability -> authorization -> residency). This module's only input is that
accepted set -- it has no access to, and no way to resurrect, anything in
`PlacementEvaluationResult.rejected`. There is no scoring path anywhere in this module
that can turn a rejected candidate into a selected one.

Priority law (enforced structurally by input shape, not by convention):

    CORRECTNESS -> SECURITY -> AUTHORIZATION -> RESIDENCY / POLICY -> CAPABILITY
        -> CAPACITY -> OPTIMIZATION / COST.

Everything left of "CAPACITY" already happened in `engine.evaluate_candidates` before
this module ever runs.

Determinism: for the same accepted-candidate list and the same scoring inputs, ranking
is deterministic. Ties are broken by `site_id` (lexicographic) as the final, always-
available tiebreaker -- never by iteration/dict order, which Python does not guarantee
stable across runs for all input shapes.

Explainability: `rank_candidates` returns, for every ranked candidate, the exact
structured factors that produced its score -- never a bare number with no justification
(this is the Group-2-scoped placement-decision data that a future P7B.33 explainability
surface will consume; this module does not itself build a user-facing explanation
product).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Tuple

from akaalEngine.fabric.placement.cost import CostConfidence, CostEstimate


class PlacementOptimizationError(ValueError):
    pass


@dataclass(frozen=True)
class OptimizationFactor:
    name: str
    value: Optional[float]
    weight: float
    contribution: Optional[float]


@dataclass(frozen=True)
class RankedCandidate:
    site_id: str
    score: float
    factors: Tuple[OptimizationFactor, ...]


def _finite_or_none(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def rank_candidates(
    accepted_site_ids: Tuple[str, ...],
    *,
    cost_by_site: Optional[Mapping[str, CostEstimate]] = None,
    proximity_score_by_site: Optional[Mapping[str, float]] = None,
    load_score_by_site: Optional[Mapping[str, float]] = None,
    cost_weight: float = 1.0,
    proximity_weight: float = 1.0,
    load_weight: float = 1.0,
) -> Tuple[RankedCandidate, ...]:
    """
    Lower `score` is better (cost-like semantics: an UNKNOWN-cost candidate never gets an
    artificial advantage or penalty purely from missing data -- its cost factor
    contributes 0.0 and is recorded as such in `factors`, so a caller inspecting the
    explanation can see the number was unknown rather than assume it was cheap).

    NaN/inf inputs (a candidate hostile-matrix scenario) are treated as "no usable
    signal" for that factor (contribution 0.0), never propagated into the score (which
    would silently poison every subsequent comparison).
    """
    cost_by_site = cost_by_site or {}
    proximity_score_by_site = proximity_score_by_site or {}
    load_score_by_site = load_score_by_site or {}

    ranked = []
    for site_id in accepted_site_ids:
        factors = []
        total = 0.0

        cost_estimate = cost_by_site.get(site_id)
        cost_value = None
        if cost_estimate is not None and cost_estimate.confidence == CostConfidence.ESTIMATED:
            cost_value = _finite_or_none(cost_estimate.estimated_total_cost)
        contribution = (cost_value * cost_weight) if cost_value is not None else 0.0
        factors.append(OptimizationFactor(name="cost", value=cost_value, weight=cost_weight, contribution=contribution))
        total += contribution

        proximity_raw = _finite_or_none(proximity_score_by_site.get(site_id))
        contribution = (proximity_raw * proximity_weight) if proximity_raw is not None else 0.0
        factors.append(OptimizationFactor(name="proximity", value=proximity_raw, weight=proximity_weight, contribution=contribution))
        total += contribution

        load_raw = _finite_or_none(load_score_by_site.get(site_id))
        contribution = (load_raw * load_weight) if load_raw is not None else 0.0
        factors.append(OptimizationFactor(name="load", value=load_raw, weight=load_weight, contribution=contribution))
        total += contribution

        ranked.append(RankedCandidate(site_id=site_id, score=total, factors=tuple(factors)))

    # Deterministic ordering: primary key is score ascending, tiebreaker is site_id
    # lexicographic -- never relies on input-list order or dict iteration order.
    ranked.sort(key=lambda c: (c.score, c.site_id))
    return tuple(ranked)
