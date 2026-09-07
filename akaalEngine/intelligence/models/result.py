"""akaalEngine.intelligence.models.result
==========================================
Result contracts for the P7C.1 Intelligence Kernel, including epistemic typing
(P7C brief §P7C.5): every statement a producer emits is tagged with what KIND of
statement it is, so a FACT is never silently presented with the same weight as a
PREDICTION or ASSUMPTION.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from akaalEngine.intelligence.models.request import IntelligenceTask


class EpistemicType(str, enum.Enum):
    FACT = "FACT"
    DERIVED_FACT = "DERIVED_FACT"
    INFERENCE = "INFERENCE"
    DIAGNOSIS = "DIAGNOSIS"
    PREDICTION = "PREDICTION"
    RECOMMENDATION = "RECOMMENDATION"
    PROPOSAL = "PROPOSAL"
    ASSUMPTION = "ASSUMPTION"


@dataclass(frozen=True)
class Explanation:
    """Auditable explanation factors (P7C brief §P7C.5). Never a hidden
    chain-of-thought dump -- a small set of concise, structured factors."""

    summary: str
    supporting_facts: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    counterfactuals: List["CounterfactualExplanation"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "supporting_facts": list(self.supporting_facts),
            "assumptions": list(self.assumptions),
            "contradictions": list(self.contradictions),
            "alternatives_considered": list(self.alternatives_considered),
            "counterfactuals": [c.to_dict() for c in self.counterfactuals],
        }


@dataclass(frozen=True)
class CounterfactualExplanation:
    """Answers 'why not alternative X?' (P7C brief §P7C.5 "Counterfactual
    explanation"). `blocking_constraint` names the concrete, checkable reason the
    alternative was excluded (e.g. a residency policy id) -- never a vague
    "not recommended". `would_require_change` states what would have to become
    true for the alternative to become eligible; this module never phrases a
    prohibited security override as if it were a normal recommendation."""

    rejected_alternative: str
    blocking_constraint: str
    would_require_change: str

    def to_dict(self) -> dict:
        return {
            "rejected_alternative": self.rejected_alternative,
            "blocking_constraint": self.blocking_constraint,
            "would_require_change": self.would_require_change,
        }


@dataclass(frozen=True)
class DiagnosticFinding:
    code: str
    severity: str
    message: str
    evidence_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class Prediction:
    metric: str
    value: float
    unit: str = ""
    low: Optional[float] = None
    high: Optional[float] = None
    basis: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "low": self.low,
            "high": self.high,
            "basis": self.basis,
        }


@dataclass(frozen=True)
class OptimizationAlternative:
    label: str
    objective_scores: Mapping[str, float] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "objective_scores": dict(self.objective_scores),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class OptimizationResult:
    objective: str
    alternatives: List[OptimizationAlternative] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "alternatives": [a.to_dict() for a in self.alternatives],
        }


@dataclass(frozen=True)
class ConfidenceEvidence:
    """Evidence-grounded confidence representation (P7C brief §P7C.5) -- deliberately
    not a single opaque percentage. `evidence_coverage` in [0,1] reflects how much of
    the relevant canonical/knowledge surface was actually consulted."""

    evidence_coverage: float
    source_agreement: Optional[float] = None
    source_freshness: Optional[str] = None
    missing_information: List[str] = field(default_factory=list)
    contradictory_evidence: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (0.0 <= self.evidence_coverage <= 1.0):
            raise ValueError("ConfidenceEvidence.evidence_coverage must be in [0.0, 1.0]")

    def to_dict(self) -> dict:
        return {
            "evidence_coverage": self.evidence_coverage,
            "source_agreement": self.source_agreement,
            "source_freshness": self.source_freshness,
            "missing_information": list(self.missing_information),
            "contradictory_evidence": list(self.contradictory_evidence),
        }


@dataclass(frozen=True)
class IntelligenceResult:
    """Immutable output of a single producer invocation. Carried inside an
    IntelligenceArtifact once persisted -- this dataclass itself is transient."""

    task: IntelligenceTask
    epistemic_type: EpistemicType
    summary: str
    explanation: Explanation
    confidence_evidence: ConfidenceEvidence
    findings: List[DiagnosticFinding] = field(default_factory=list)
    predictions: List[Prediction] = field(default_factory=list)
    optimization: Optional[OptimizationResult] = None
    data: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task": self.task.value,
            "epistemic_type": self.epistemic_type.value,
            "summary": self.summary,
            "explanation": self.explanation.to_dict(),
            "confidence_evidence": self.confidence_evidence.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "predictions": [p.to_dict() for p in self.predictions],
            "optimization": self.optimization.to_dict() if self.optimization else None,
            "data": dict(self.data),
        }
