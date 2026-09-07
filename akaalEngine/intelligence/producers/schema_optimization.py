"""akaalEngine.intelligence.producers.schema_optimization
===========================================================
P7C.10 -- Schema & Data Model Optimization. Deterministic structural heuristics
over the canonical schema model (akaalEngine.schema.models.table.CanonicalTable /
CanonicalIndex) -- redundant-index detection, missing-FK-covering-index detection.
Every recommendation is classified per the P7C brief's three-way taxonomy so an
optional target-native improvement is never silently conflated with a required
compatibility conversion or a semantic change that needs human review. No
capability not actually supported by the target provider is ever recommended --
capability awareness is delegated to the caller-supplied `provider_capability_checker`.
"""

from __future__ import annotations

from dataclasses import dataclass
import enum
from typing import Callable, List, Optional

from akaalEngine.intelligence.models.context import IntelligenceContext
from akaalEngine.intelligence.models.request import IntelligenceRequest
from akaalEngine.intelligence.models.result import (
    ConfidenceEvidence,
    DiagnosticFinding,
    EpistemicType,
    Explanation,
    IntelligenceResult,
)


class OptimizationClassification(str, enum.Enum):
    REQUIRED_COMPATIBILITY_CONVERSION = "REQUIRED_COMPATIBILITY_CONVERSION"
    OPTIONAL_TARGET_OPTIMIZATION = "OPTIONAL_TARGET_OPTIMIZATION"
    SEMANTIC_CHANGE_REQUIRING_REVIEW = "SEMANTIC_CHANGE_REQUIRING_REVIEW"


@dataclass(frozen=True)
class SchemaOptimizationRecommendation:
    classification: OptimizationClassification
    table: str
    description: str
    rationale: str

    def to_dict(self) -> dict:
        return {
            "classification": self.classification.value,
            "table": self.table,
            "description": self.description,
            "rationale": self.rationale,
        }


def _is_prefix(shorter, longer) -> bool:
    return len(shorter) <= len(longer) and tuple(longer[: len(shorter)]) == tuple(shorter)


def detect_redundant_indexes(table) -> List[SchemaOptimizationRecommendation]:
    """A non-unique index whose column list is a prefix of another index's column
    list on the same table is redundant -- the longer index already serves every
    query the shorter one could. Unique/primary indexes are never flagged
    (dropping one would be a semantic change, not a pure optimization)."""
    recs: List[SchemaOptimizationRecommendation] = []
    indexes = list(getattr(table, "indexes", ()) or ())
    for i, idx in enumerate(indexes):
        if idx.is_unique or idx.is_primary:
            continue
        for j, other in enumerate(indexes):
            if i == j or other.is_unique or other.is_primary:
                continue
            if idx.columns == other.columns:
                continue
            if _is_prefix(idx.columns, other.columns):
                recs.append(
                    SchemaOptimizationRecommendation(
                        classification=OptimizationClassification.OPTIONAL_TARGET_OPTIMIZATION,
                        table=getattr(table, "qualified_name", table.table_name),
                        description=f"Index {idx.name!r} ({list(idx.columns)}) is redundant with {other.name!r} ({list(other.columns)}).",
                        rationale="A non-unique index whose columns are a strict prefix of another index's columns "
                        "on the same table adds write/storage overhead without serving any query the longer "
                        "index cannot already serve.",
                    )
                )
                break
    return recs


def detect_missing_fk_covering_index(table) -> List[SchemaOptimizationRecommendation]:
    """A foreign-key column with no index covering it as a leading column
    typically causes slow joins/cascades -- flag as an optional optimization
    (adding an index changes nothing semantically)."""
    recs: List[SchemaOptimizationRecommendation] = []
    indexes = list(getattr(table, "indexes", ()) or ())
    covered_leading_columns = {idx.columns[0] for idx in indexes if idx.columns}
    pk = getattr(table, "primary_key", None)
    if pk and getattr(pk, "columns", None):
        covered_leading_columns.add(pk.columns[0])

    for fk in getattr(table, "foreign_keys", ()) or ():
        if not fk.columns:
            continue
        leading_fk_col = fk.columns[0]
        if leading_fk_col not in covered_leading_columns:
            recs.append(
                SchemaOptimizationRecommendation(
                    classification=OptimizationClassification.OPTIONAL_TARGET_OPTIMIZATION,
                    table=getattr(table, "qualified_name", table.table_name),
                    description=f"Foreign key column {leading_fk_col!r} (constraint {fk.name!r}) has no covering index.",
                    rationale="Uncovered FK columns commonly cause full-table-scan joins and slow cascade "
                    "operations on the target engine; adding an index is purely additive and non-semantic.",
                )
            )
    return recs


ProviderCapabilityChecker = Callable[[str], bool]


def make_schema_optimization_producer(
    schema_model_resolver,
    provider_capability_checker: Optional[ProviderCapabilityChecker] = None,
):
    """IntelligenceKernel-compatible producer for IntelligenceTask.OPTIMIZE,
    capability='schema_optimization'. `schema_model_resolver(request, context)`
    returns a CanonicalSchemaModel; this producer performs no discovery.
    `provider_capability_checker(feature_name)` -- if given, filters out any
    recommendation whose enabling feature is not supported by the target
    provider (P7C brief 'Capability awareness': never recommend a target feature
    the actual target/provider capability does not support)."""

    def producer(request: IntelligenceRequest, context: IntelligenceContext) -> IntelligenceResult:
        model = schema_model_resolver(request, context)
        tables = list(getattr(model, "tables", ()) or ())

        recommendations: List[SchemaOptimizationRecommendation] = []
        for table in tables:
            recommendations.extend(detect_redundant_indexes(table))
            recommendations.extend(detect_missing_fk_covering_index(table))

        if provider_capability_checker is not None:
            recommendations = [
                r for r in recommendations
                if r.classification != OptimizationClassification.OPTIONAL_TARGET_OPTIMIZATION
                or provider_capability_checker("secondary_index")
            ]

        findings = [
            DiagnosticFinding(
                code=f"SCHEMA_OPT:{r.classification.value}",
                severity="LOW",
                message=r.description,
                evidence_refs=[r.table],
            )
            for r in recommendations
        ]

        return IntelligenceResult(
            task=request.task,
            epistemic_type=EpistemicType.RECOMMENDATION,
            summary=f"{len(recommendations)} optional target-native schema optimization(s) identified "
            f"across {len(tables)} table(s); zero required-compatibility or semantic-review changes proposed here.",
            explanation=Explanation(
                summary="Deterministic structural heuristics over CanonicalTable index/FK metadata.",
                supporting_facts=[f"tables_scanned={len(tables)}", f"recommendations={len(recommendations)}"],
            ),
            confidence_evidence=ConfidenceEvidence(evidence_coverage=1.0),
            findings=findings,
            data={"recommendations": [r.to_dict() for r in recommendations]},
        )

    return producer
