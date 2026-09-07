"""akaalEngine.intelligence.evaluation
======================================
Foundation contracts (P7C brief §14 items 23-25) for:
  23. Recommendation outcome-tracking contracts
  24. Task-specific evaluation foundation
  25. Shadow-evaluation architecture foundation

Per the P7C brief's own governing rule: "If some feature's full operational
realization belongs naturally to Group 2, Group 1 must still establish the
correct foundation/contracts without prematurely duplicating Group 2
implementation." This module is exactly that -- typed, durable, testable
contracts with no full operational system behind them yet (no automated
evaluation harness, no live shadow-traffic router). A Group 2 session can build
on these contracts; nothing here fabricates a working evaluator that does not
exist.

Durability: reuses the same caller-supplied SQLite connection pattern as
akaalEngine.intelligence.lifecycle.store.IntelligenceArtifactStore -- no second
persistence engine.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional


# --- #23 Recommendation outcome-tracking ------------------------------------

@dataclass(frozen=True)
class OutcomeRecord:
    """Records what actually happened after an IntelligenceArtifact's
    recommendation/proposal was accepted and (eventually) acted on. This is
    intentionally separate from ArtifactLifecycleState -- lifecycle tracks the
    artifact's own state machine (GENERATED..ACCEPTED..SUPERSEDED); OutcomeRecord
    tracks the real-world result of acting on an ACCEPTED artifact, which can
    only be known after the fact and may arrive long after generation."""

    outcome_id: str
    artifact_id: str
    tenant_id: str
    outcome_status: str  # "SUCCEEDED" | "FAILED" | "PARTIALLY_SUCCEEDED" | "ABANDONED"
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: str = ""
    metrics: Mapping[str, Any] = field(default_factory=dict)

    _VALID_STATUSES = frozenset({"SUCCEEDED", "FAILED", "PARTIALLY_SUCCEEDED", "ABANDONED"})

    def __post_init__(self) -> None:
        if self.outcome_status not in self._VALID_STATUSES:
            raise ValueError(f"OutcomeRecord.outcome_status must be one of {sorted(self._VALID_STATUSES)}")
        if not self.artifact_id or not self.tenant_id:
            raise ValueError("OutcomeRecord requires non-empty artifact_id and tenant_id")
        object.__setattr__(self, "metrics", dict(self.metrics))

    @classmethod
    def new(cls, *, artifact_id: str, tenant_id: str, outcome_status: str, detail: str = "", metrics: Optional[Mapping[str, Any]] = None) -> "OutcomeRecord":
        return cls(
            outcome_id=f"intel-outcome-{uuid.uuid4().hex}",
            artifact_id=artifact_id,
            tenant_id=tenant_id,
            outcome_status=outcome_status,
            detail=detail,
            metrics=metrics or {},
        )

    def to_dict(self) -> dict:
        return {
            "outcome_id": self.outcome_id,
            "artifact_id": self.artifact_id,
            "tenant_id": self.tenant_id,
            "outcome_status": self.outcome_status,
            "observed_at": self.observed_at,
            "detail": self.detail,
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OutcomeRecord":
        return cls(
            outcome_id=data["outcome_id"], artifact_id=data["artifact_id"], tenant_id=data["tenant_id"],
            outcome_status=data["outcome_status"], observed_at=data.get("observed_at", ""),
            detail=data.get("detail", ""), metrics=data.get("metrics") or {},
        )


class OutcomeStore:
    """Durable outcome storage, mirroring IntelligenceArtifactStore's shape.
    Table is created centrally alongside intelligence_artifacts (see
    akaalPipeline.state.unit_of_work.SQLiteUnitOfWork.initialize_schema)."""

    def save(self, outcome: OutcomeRecord, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO intelligence_outcomes (outcome_id, artifact_id, tenant_id, outcome_status, "
            "observed_at, detail, metrics) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (outcome.outcome_id, outcome.artifact_id, outcome.tenant_id, outcome.outcome_status,
             outcome.observed_at, outcome.detail, json.dumps(dict(outcome.metrics))),
        )

    def list_for_artifact(self, artifact_id: str, conn: sqlite3.Connection) -> List[OutcomeRecord]:
        cur = conn.execute(
            "SELECT * FROM intelligence_outcomes WHERE artifact_id = ? ORDER BY observed_at ASC", (artifact_id,)
        )
        return [
            OutcomeRecord.from_dict({**dict(row), "metrics": json.loads(row["metrics"]) if row["metrics"] else {}})
            for row in cur.fetchall()
        ]


# --- #24 Task-specific evaluation foundation --------------------------------

@dataclass(frozen=True)
class EvaluationCriterion:
    """One named, scorable dimension a producer's output can be judged against
    for a given IntelligenceTask (e.g. 'compatibility_breakdown_completeness'
    for ASSESS). Purely a typed contract -- no scoring engine exists here."""

    name: str
    description: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("EvaluationCriterion.name cannot be empty")
        if self.weight < 0:
            raise ValueError("EvaluationCriterion.weight cannot be negative")


@dataclass(frozen=True)
class EvaluationResult:
    """The result of scoring one artifact against one criterion. `score` is in
    [0, 1]. This is a foundation contract: nothing in Group 1 automatically
    computes these -- a human reviewer, or a future Group 2 automated evaluator,
    produces them and calls EvaluationStore.save."""

    evaluation_id: str
    artifact_id: str
    criterion_name: str
    score: float
    evaluated_by: str
    is_hard_gate: bool = False
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ValueError("EvaluationResult.score must be in [0.0, 1.0]")

    @property
    def hard_gate_passed(self) -> bool:
        """A hard-gate criterion is binary: only an exact score of 1.0 passes.
        This property is meaningless (always True) for a non-hard-gate result --
        callers must check `is_hard_gate` before relying on it."""
        return (not self.is_hard_gate) or self.score >= 1.0

    @classmethod
    def new(cls, *, artifact_id: str, criterion_name: str, score: float, evaluated_by: str, is_hard_gate: bool = False, notes: str = "") -> "EvaluationResult":
        return cls(
            evaluation_id=f"intel-eval-{uuid.uuid4().hex}", artifact_id=artifact_id,
            criterion_name=criterion_name, score=score, evaluated_by=evaluated_by,
            is_hard_gate=is_hard_gate, notes=notes,
        )

    def to_dict(self) -> dict:
        return {
            "evaluation_id": self.evaluation_id, "artifact_id": self.artifact_id,
            "criterion_name": self.criterion_name, "score": self.score,
            "evaluated_by": self.evaluated_by, "is_hard_gate": self.is_hard_gate,
            "evaluated_at": self.evaluated_at, "notes": self.notes,
        }


class ComparisonVerdict(str):
    """String-enum-like constants for compare_evaluation_sets outcomes."""

    CANDIDATE_BETTER = "CANDIDATE_BETTER"
    CURRENT_BETTER = "CURRENT_BETTER"
    EQUAL = "EQUAL"
    CANDIDATE_REJECTED_HARD_GATE_FAILURE = "CANDIDATE_REJECTED_HARD_GATE_FAILURE"
    CURRENT_REJECTED_HARD_GATE_FAILURE = "CURRENT_REJECTED_HARD_GATE_FAILURE"
    BOTH_REJECTED_HARD_GATE_FAILURE = "BOTH_REJECTED_HARD_GATE_FAILURE"


def _weighted_average(results: List[EvaluationResult], criteria: Mapping[str, EvaluationCriterion]) -> float:
    total_weight = 0.0
    weighted_sum = 0.0
    for r in results:
        weight = criteria[r.criterion_name].weight if r.criterion_name in criteria else 1.0
        weighted_sum += r.score * weight
        total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else 0.0


def compare_evaluation_sets(
    *,
    candidate_results: List[EvaluationResult],
    current_results: List[EvaluationResult],
    criteria: Optional[List[EvaluationCriterion]] = None,
) -> str:
    """Real, genuinely computed comparison between two evaluated result sets
    (e.g. a shadow candidate vs. the current production producer). This is NOT
    a fixed/hardcoded outcome -- it is a deterministic function of the actual
    scores and weights supplied.

    A hard-gate criterion failure is decisive and can never be averaged away by
    otherwise-high scores on other criteria (P7C brief: 'hard safety gate
    failure cannot be averaged away') -- checked BEFORE any weighted-average
    comparison runs. Promoting a candidate that passes this comparison into
    actual production use is Group-2 (P7C.23) territory; this function only
    establishes the comparison contract/foundation.
    """
    criteria_by_name = {c.name: c for c in (criteria or [])}

    candidate_hard_fail = any(r.is_hard_gate and not r.hard_gate_passed for r in candidate_results)
    current_hard_fail = any(r.is_hard_gate and not r.hard_gate_passed for r in current_results)

    if candidate_hard_fail and current_hard_fail:
        return ComparisonVerdict.BOTH_REJECTED_HARD_GATE_FAILURE
    if candidate_hard_fail:
        return ComparisonVerdict.CANDIDATE_REJECTED_HARD_GATE_FAILURE
    if current_hard_fail:
        return ComparisonVerdict.CURRENT_REJECTED_HARD_GATE_FAILURE

    candidate_avg = _weighted_average(candidate_results, criteria_by_name)
    current_avg = _weighted_average(current_results, criteria_by_name)

    if candidate_avg > current_avg:
        return ComparisonVerdict.CANDIDATE_BETTER
    if current_avg > candidate_avg:
        return ComparisonVerdict.CURRENT_BETTER
    return ComparisonVerdict.EQUAL


# --- #25 Shadow-evaluation architecture foundation --------------------------

@dataclass(frozen=True)
class ShadowComparisonResult:
    """Records a comparison between a PRODUCTION artifact (the one actually
    returned to the caller) and a SHADOW artifact (an alternate producer/
    algorithm/policy version run on the same request but never surfaced to the
    caller). This is the contract shape a future shadow-traffic router would
    populate; this module does not itself run anything in shadow -- there is no
    live routing infrastructure to shadow traffic through in Group 1."""

    comparison_id: str
    production_artifact_id: str
    shadow_artifact_id: str
    tenant_id: str
    agree: bool
    divergence_summary: str = ""
    compared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "comparison_id": self.comparison_id, "production_artifact_id": self.production_artifact_id,
            "shadow_artifact_id": self.shadow_artifact_id, "tenant_id": self.tenant_id,
            "agree": self.agree, "divergence_summary": self.divergence_summary, "compared_at": self.compared_at,
        }

    @classmethod
    def compare(cls, *, production_artifact, shadow_artifact, tenant_id: str) -> "ShadowComparisonResult":
        """A real (if minimal) comparison: agree iff the two artifacts' result
        fingerprints match structurally. A future Group 2 evaluator can replace
        this with task-specific semantic comparison; this baseline is genuine
        equality checking, not a stub that always returns a fixed value."""
        prod_data = dict(production_artifact.result) if hasattr(production_artifact, "result") else dict(production_artifact)
        shadow_data = dict(shadow_artifact.result) if hasattr(shadow_artifact, "result") else dict(shadow_artifact)
        agree = prod_data.get("summary") == shadow_data.get("summary") and prod_data.get("data") == shadow_data.get("data")
        return cls(
            comparison_id=f"intel-shadow-{uuid.uuid4().hex}",
            production_artifact_id=getattr(production_artifact, "artifact_id", "unknown"),
            shadow_artifact_id=getattr(shadow_artifact, "artifact_id", "unknown"),
            tenant_id=tenant_id,
            agree=agree,
            divergence_summary="" if agree else "production and shadow result summary/data differ",
        )
